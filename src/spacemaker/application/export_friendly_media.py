from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from spacemaker.domain.gallery_batch import CpuEncodeConfirmationRequired, VideoExportEncoder
from spacemaker.domain.gallery_cache_paths import export_cache_path
from spacemaker.domain.gallery_export import (
	ExportFormat,
	is_friendly_h264_aac_mp4,
	is_friendly_jpeg_filename,
)
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.library_paths import EXPORTS_DIR_NAME
from spacemaker.domain.media import media_kind_for_filename
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.media_converter import MediaConverterPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


@dataclass(frozen=True, slots=True)
class ExportResult:
	download_path: str
	skipped_encode: bool


class ExportFriendlyMedia:
	def __init__(
		self,
		filesystem: FileSystemPort,
		converter: MediaConverterPort,
		probe: MediaProbePort,
	) -> None:
		self._filesystem = filesystem
		self._converter = converter
		self._probe = probe

	def exports_dir(self, library_root: str) -> str:
		return str(Path(library_root) / EXPORTS_DIR_NAME)

	def needs_encode(self, library_root: str, relative_path: str, export_format: ExportFormat) -> bool:
		"""True when exporting would run an encoder: not already friendly and no up-to-date cache copy."""
		source = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative_path)
		if not self._filesystem.exists(source):
			return False
		if export_format is ExportFormat.JPEG and is_friendly_jpeg_filename(relative_path):
			return False
		if export_format is ExportFormat.H264_AAC and is_friendly_h264_aac_mp4(self._probe.probe_video(source)):
			return False
		dest = Path(export_cache_path(library_root, relative_path, export_format))
		return not self._is_fresh_cache(dest, Path(source))

	def _video_encoder_uses_cpu(self, allow_cpu_encode: bool) -> bool:
		encoder = self._converter.friendly_video_encoder()
		if encoder is VideoExportEncoder.NONE:
			raise ValueError("MP4 export is not available on this computer")
		use_cpu = encoder is VideoExportEncoder.CPU_H264
		if use_cpu and not allow_cpu_encode:
			raise CpuEncodeConfirmationRequired(1)
		return use_cpu

	def preflight(
		self, library_root: str, relative_path: str, export_format: ExportFormat, *, allow_cpu_encode: bool
	) -> None:
		"""Synchronous check before a single export job starts: raises CpuEncodeConfirmationRequired
		(or ValueError when no H.264 encoder exists) only if this export would really encode a video."""
		if export_format is ExportFormat.H264_AAC and self.needs_encode(library_root, relative_path, export_format):
			self._video_encoder_uses_cpu(allow_cpu_encode)

	@staticmethod
	def _is_fresh_cache(dest: Path, source_path: Path) -> bool:
		return dest.is_file() and dest.stat().st_size > 0 and dest.stat().st_mtime >= source_path.stat().st_mtime

	def run(
		self,
		library_root: str,
		relative_path: str,
		export_format: ExportFormat,
		*,
		on_progress: Callable[[int], None] | None = None,
		allow_cpu_encode: bool = False,
	) -> ExportResult:
		source = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative_path)
		if not self._filesystem.exists(source):
			raise FileNotFoundError(relative_path)
		source_path = Path(source)
		kind = media_kind_for_filename(relative_path)
		if export_format is ExportFormat.JPEG and kind.value != "image":
			raise ValueError("JPEG export requires an image")
		if export_format is ExportFormat.H264_AAC and kind.value != "video":
			raise ValueError("MP4 export requires a video")

		if export_format is ExportFormat.JPEG and is_friendly_jpeg_filename(relative_path):
			if on_progress:
				on_progress(100)
			return ExportResult(download_path=str(source_path.resolve()), skipped_encode=True)

		if export_format is ExportFormat.H264_AAC:
			probe = self._probe.probe_video(str(source_path))
			if is_friendly_h264_aac_mp4(probe):
				if on_progress:
					on_progress(100)
				return ExportResult(download_path=str(source_path.resolve()), skipped_encode=True)

		dest = Path(export_cache_path(library_root, relative_path, export_format))
		if self._is_fresh_cache(dest, source_path):
			if on_progress:
				on_progress(100)
			return ExportResult(download_path=str(dest.resolve()), skipped_encode=False)

		use_cpu = False
		if export_format is ExportFormat.H264_AAC:
			use_cpu = self._video_encoder_uses_cpu(allow_cpu_encode)

		dest.parent.mkdir(parents=True, exist_ok=True)
		# Encode beside the cache entry and rename on success: a failed/interrupted export must never
		# leave a half-written file that the "non-empty and newer than source" check would serve.
		staging = dest.with_name(f".{uuid.uuid4().hex}.partial{dest.suffix}")
		if on_progress:
			on_progress(5)
		try:
			if export_format is ExportFormat.JPEG:
				self._converter.encode_image_to_jpeg(str(source_path), str(staging))
				if on_progress:
					on_progress(100)
			else:
				self._converter.encode_video_to_h264_aac(
					str(source_path),
					str(staging),
					on_progress=on_progress,
					use_cpu=use_cpu,
				)
			os.replace(staging, dest)
		finally:
			staging.unlink(missing_ok=True)
		return ExportResult(download_path=str(dest.resolve()), skipped_encode=False)
