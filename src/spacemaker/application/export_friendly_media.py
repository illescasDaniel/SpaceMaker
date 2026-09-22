from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from spacemaker.domain.gallery_export import (
	ExportFormat,
	export_cache_filename,
	is_friendly_h264_aac_mp4,
	is_friendly_jpeg_filename,
)
from spacemaker.domain.library import LibraryFolder
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
		return str(Path(library_root) / ".exports")

	def run(
		self,
		library_root: str,
		relative_path: str,
		export_format: ExportFormat,
		*,
		on_progress: Callable[[int], None] | None = None,
	) -> ExportResult:
		source = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, relative_path)
		if not self._filesystem.exists(source):
			raise FileNotFoundError(relative_path)
		source_path = Path(source)
		stat = source_path.stat()
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

		cache_name = export_cache_filename(
			relative_path,
			stat.st_mtime_ns,
			stat.st_size,
			export_format,
		)
		dest = Path(self.exports_dir(library_root)) / cache_name
		if dest.is_file() and dest.stat().st_size > 0:
			if on_progress:
				on_progress(100)
			return ExportResult(download_path=str(dest.resolve()), skipped_encode=False)

		dest.parent.mkdir(parents=True, exist_ok=True)
		if on_progress:
			on_progress(5)
		if export_format is ExportFormat.JPEG:
			self._converter.encode_image_to_jpeg(str(source_path), str(dest))
			if on_progress:
				on_progress(100)
		else:
			self._converter.encode_video_to_h264_aac(
				str(source_path),
				str(dest),
				on_progress=on_progress,
			)
		return ExportResult(download_path=str(dest.resolve()), skipped_encode=False)
