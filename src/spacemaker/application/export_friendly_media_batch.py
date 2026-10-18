from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.domain.gallery_batch import (
	ArchiveEntry,
	BatchConvertItemResult,
	BatchConvertOutcome,
	BatchProgress,
	CpuEncodeConfirmationRequired,
	GalleryBatchError,
	InsufficientDiskSpaceError,
	VideoExportEncoder,
	assign_zip_entry_names,
	is_batch_artifact_expired,
	normalize_batch_paths,
	required_free_bytes,
)
from spacemaker.domain.gallery_cache_paths import batch_export_job_dir, batch_exports_root
from spacemaker.domain.gallery_export import ExportFormat
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import MediaKind, media_kind_for_filename
from spacemaker.ports.outbound.archive_writer import ArchiveWriterPort
from spacemaker.ports.outbound.disk_space import DiskSpacePort
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.media_converter import FriendlyVideoExportPort
from spacemaker.ports.outbound.media_probe import MediaProbePort


_JOB_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
ARCHIVE_FILE_NAME = "SpaceMaker-export.zip"


def _format_for(relative_path: str) -> ExportFormat | None:
	kind = media_kind_for_filename(relative_path)
	if kind is MediaKind.IMAGE:
		return ExportFormat.JPEG
	if kind is MediaKind.VIDEO:
		return ExportFormat.H264_AAC
	return None


@dataclass(frozen=True, slots=True)
class BatchConvertResult:
	results: tuple[BatchConvertItemResult, ...]
	# Absolute path of the finished zip; "" when no item succeeded (no download is offered).
	archive_path: str


class ExportFriendlyMediaBatch:
	"""Inbound use case: convert a selection to JPEG / MP4 and zip the outputs.

	Spec: specs/gallery-batch/SPEC.md. Reuses ``ExportFriendlyMedia`` per item (so already-friendly
	files pass through and up-to-date ``.exports/`` copies are reused); a failing item is skipped and
	never aborts the batch.
	"""

	def __init__(
		self,
		export_friendly: ExportFriendlyMedia,
		video_export: FriendlyVideoExportPort,
		probe: MediaProbePort,
		filesystem: FileSystemPort,
		disk_space: DiskSpacePort,
		archive_writer: ArchiveWriterPort,
	) -> None:
		self._export_friendly = export_friendly
		self._video_export = video_export
		self._probe = probe
		self._filesystem = filesystem
		self._disk_space = disk_space
		self._archive_writer = archive_writer

	def preflight(
		self,
		library_root: str,
		relative_paths: Sequence[str],
		*,
		allow_cpu_encode: bool,
	) -> tuple[str, ...]:
		"""Synchronous checks done before a job is created; returns the normalized paths.

		Raises UnsafeBatchPathError, BatchTooLargeError, InsufficientDiskSpaceError, and
		CpuEncodeConfirmationRequired (count of videos that need a CPU re-encode: no hardware H.264
		encoder, not already friendly, no up-to-date ``.exports/`` copy) when ``allow_cpu_encode`` is False.
		"""
		paths = normalize_batch_paths(relative_paths)
		reencode_sizes: list[int] = []
		passthrough_sizes: list[int] = []
		cpu_videos = 0
		cpu_encoder = self._video_export.friendly_video_encoder() is VideoExportEncoder.CPU_H264
		for relative in paths:
			export_format = _format_for(relative)
			source = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative)
			if export_format is None or not self._filesystem.exists(source):
				continue
			size = self._filesystem.file_size(source)
			if self._export_friendly.needs_encode(library_root, relative, export_format):
				reencode_sizes.append(size)
				if export_format is ExportFormat.H264_AAC:
					cpu_videos += 1
			else:
				passthrough_sizes.append(size)
		required = required_free_bytes(reencode_sizes, passthrough_sizes)
		available = self._disk_space.free_bytes(batch_exports_root(library_root))
		if available < required:
			raise InsufficientDiskSpaceError(required, available)
		if cpu_encoder and cpu_videos and not allow_cpu_encode:
			raise CpuEncodeConfirmationRequired(cpu_videos)
		return paths

	def run(
		self,
		library_root: str,
		job_id: str,
		relative_paths: Sequence[str],
		*,
		allow_cpu_encode: bool,
		on_progress: Callable[[BatchProgress], None] | None = None,
	) -> BatchConvertResult:
		"""Convert items one at a time and write the stored zip under ``.exports/.batch/{job_id}/``.

		Photos → JPEG; videos → H.264 + AAC MP4 (hardware, or ``libx264`` only when ``allow_cpu_encode``).
		A video with no H.264 encoder at all is skipped with “MP4 not available on this computer”.
		No archive is written when every item is skipped.
		"""
		paths = normalize_batch_paths(relative_paths)
		count = len(paths)
		results: list[BatchConvertItemResult] = []
		for index, relative in enumerate(paths):

			def report(percent: int, index: int = index) -> None:
				if on_progress:
					on_progress(BatchProgress(index, count, max(0, min(100, percent))))

			results.append(self._convert_one(library_root, relative, allow_cpu_encode, report))
			report(100)
		named = {r.relative_path: r for r in assign_zip_entry_names(results)}
		results = [named.get(r.relative_path, r) for r in results]
		if not named:
			return BatchConvertResult(tuple(results), "")
		destination = str(Path(batch_export_job_dir(library_root, job_id)) / ARCHIVE_FILE_NAME)
		entries = [ArchiveEntry(r.output_path, r.archive_name) for r in named.values()]
		self._archive_writer.write_stored_zip(destination, entries)
		return BatchConvertResult(tuple(results), destination)

	def preflight_download(self, library_root: str, relative_paths: Sequence[str]) -> tuple[str, ...]:
		"""Like ``preflight`` for **Download**: stored files are zipped unchanged, so the only checks are
		path validation (UnsafeBatchPathError, BatchTooLargeError) and free disk space for the zip
		(InsufficientDiskSpaceError); there is never a CPU confirmation. Spec: specs/gallery-batch/SPEC.md."""
		paths = normalize_batch_paths(relative_paths)
		sizes: list[int] = []
		for relative in paths:
			source = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative)
			if self._filesystem.exists(source):
				sizes.append(self._filesystem.file_size(source))
		required = required_free_bytes([], sizes)
		available = self._disk_space.free_bytes(batch_exports_root(library_root))
		if available < required:
			raise InsufficientDiskSpaceError(required, available)
		return paths

	def run_download(
		self,
		library_root: str,
		job_id: str,
		relative_paths: Sequence[str],
		*,
		on_progress: Callable[[BatchProgress], None] | None = None,
	) -> BatchConvertResult:
		"""Zip the stored ``processed/`` files byte-for-byte (no converter call) at
		``.exports/.batch/{job_id}/SpaceMaker-export.zip``; missing files are SKIPPED with a reason,
		the rest are PASSED_THROUGH; no archive when everything is skipped."""
		paths = normalize_batch_paths(relative_paths)
		count = len(paths)
		results: list[BatchConvertItemResult] = []
		for index, relative in enumerate(paths):
			source = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative)
			if self._filesystem.exists(source):
				results.append(BatchConvertItemResult(relative, BatchConvertOutcome.PASSED_THROUGH, output_path=source))
			else:
				results.append(
					BatchConvertItemResult(relative, BatchConvertOutcome.SKIPPED, reason="File no longer exists")
				)
			if on_progress:
				on_progress(BatchProgress(index, count, 100))
		named = {r.relative_path: r for r in assign_zip_entry_names(results)}
		results = [named.get(r.relative_path, r) for r in results]
		if not named:
			return BatchConvertResult(tuple(results), "")
		destination = str(Path(batch_export_job_dir(library_root, job_id)) / ARCHIVE_FILE_NAME)
		entries = [ArchiveEntry(r.output_path, r.archive_name) for r in named.values()]
		self._archive_writer.write_stored_zip(destination, entries)
		return BatchConvertResult(tuple(results), destination)

	def _convert_one(
		self,
		library_root: str,
		relative: str,
		allow_cpu_encode: bool,
		report: Callable[[int], None],
	) -> BatchConvertItemResult:
		export_format = _format_for(relative)
		if export_format is None:
			return BatchConvertItemResult(relative, BatchConvertOutcome.SKIPPED, reason="Not a photo or video")
		try:
			exported = self._export_friendly.run(
				library_root,
				relative,
				export_format,
				on_progress=report,
				allow_cpu_encode=allow_cpu_encode,
			)
		except FileNotFoundError:
			return BatchConvertItemResult(relative, BatchConvertOutcome.SKIPPED, reason="File no longer exists")
		except (ValueError, GalleryBatchError) as error:
			return BatchConvertItemResult(relative, BatchConvertOutcome.SKIPPED, reason=str(error))
		except Exception:  # noqa: BLE001 - one bad item must never abort the batch
			return BatchConvertItemResult(relative, BatchConvertOutcome.SKIPPED, reason="Could not convert")
		if exported.skipped_encode:
			return BatchConvertItemResult(
				relative, BatchConvertOutcome.PASSED_THROUGH, output_path=exported.download_path
			)
		return BatchConvertItemResult(
			relative, BatchConvertOutcome.CONVERTED, export_format=export_format, output_path=exported.download_path
		)

	def delete_job(self, library_root: str, job_id: str) -> None:
		"""Remove one job folder (after its zip was downloaded or its job was dismissed)."""
		if not _JOB_ID_PATTERN.fullmatch(job_id):
			raise ValueError("invalid job id")
		self._filesystem.delete_directory(batch_export_job_dir(library_root, job_id))

	def sweep(
		self,
		library_root: str,
		*,
		now: float,
		keep_job_ids: frozenset[str] = frozenset(),
		expire_all: bool = False,
	) -> None:
		"""Delete batch job folders older than 24 h, or all of them at app start (``expire_all``);
		``keep_job_ids`` protects jobs still running or not yet expired."""
		root = batch_exports_root(library_root)
		newest: dict[str, float] = {}
		for relative in self._filesystem.list_files_recursive(root):
			job_id = relative.split("/", 1)[0]
			stat = self._filesystem.file_stat(str(Path(root) / relative))
			newest[job_id] = max(newest.get(job_id, 0.0), stat.mtime)
		for job_id, mtime in newest.items():
			if job_id in keep_job_ids:
				continue
			if expire_all or is_batch_artifact_expired(now - mtime):
				self._filesystem.delete_directory(str(Path(root) / job_id))
