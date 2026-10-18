from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase, is_safe_gallery_relative_path


# Spec: specs/gallery-batch/SPEC.md (Design decisions → Performance & resource budget).
MAX_GALLERY_BATCH_ITEMS = 500
BATCH_ARTIFACT_MAX_AGE_SECONDS = 24 * 60 * 60


class VideoExportEncoder(StrEnum):
	"""Encoder a friendly MP4 export would use on this host (never used for library convert)."""

	HARDWARE_H264 = "hardware_h264"
	CPU_H264 = "cpu_h264"
	NONE = "none"


class GalleryBatchError(Exception):
	"""Base class for batch request failures raised before any file is touched."""


class UnsafeBatchPathError(GalleryBatchError):
	"""A batch path is not a safe relative path inside processed/ (maps to HTTP 403)."""


class BatchTooLargeError(GalleryBatchError):
	"""More than MAX_GALLERY_BATCH_ITEMS distinct paths were requested (maps to HTTP 400)."""


class InsufficientDiskSpaceError(GalleryBatchError):
	"""Free space is below the batch estimate; nothing was started."""

	def __init__(self, required_bytes: int, available_bytes: int) -> None:
		super().__init__(f"need {required_bytes} bytes free, {available_bytes} available")
		self.required_bytes = required_bytes
		self.available_bytes = available_bytes


class CpuEncodeConfirmationRequired(GalleryBatchError):
	"""MP4 re-encode would use the CPU and the caller did not confirm it (maps to HTTP 409).

	Raised for the single-item export and for a batch; the client shows Continue / Cancel and
	retries with ``allow_cpu_encode=True`` on Continue.
	"""

	def __init__(self, video_count: int) -> None:
		super().__init__(f"{video_count} video(s) need CPU encoding")
		self.video_count = video_count


class TrashError(OSError):
	"""The platform Trash refused or cannot take a file. The file is left untouched."""


class TrashOutcome(StrEnum):
	TRASHED = "trashed"
	ALREADY_GONE = "already_gone"
	FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TrashItemResult:
	relative_path: str
	outcome: TrashOutcome
	reason: str = ""

	def to_dict(self) -> dict[str, object]:
		return {"relative_path": self.relative_path, "outcome": self.outcome.value, "reason": self.reason}


class BatchConvertOutcome(StrEnum):
	CONVERTED = "converted"
	PASSED_THROUGH = "passed_through"
	SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class BatchConvertItemResult:
	relative_path: str
	outcome: BatchConvertOutcome
	export_format: ExportFormat | None = None
	reason: str = ""
	# Absolute path of the file that goes into the zip (stored original or .exports/ copy); "" when skipped.
	output_path: str = ""
	# Name inside the zip; assigned by assign_zip_entry_names, "" when skipped.
	archive_name: str = ""

	def to_dict(self) -> dict[str, object]:
		return {
			"relative_path": self.relative_path,
			"outcome": self.outcome.value,
			"reason": self.reason,
		}


@dataclass(frozen=True, slots=True)
class BatchProgress:
	"""Per-item plus overall progress reported to the job while a batch converts."""

	item_index: int
	item_count: int
	item_percent: int

	@property
	def overall_percent(self) -> int:
		if self.item_count <= 0:
			return 100
		done = self.item_index * 100 + self.item_percent
		return min(100, done // self.item_count)


@dataclass(frozen=True, slots=True)
class ArchiveEntry:
	source_path: str
	entry_name: str


class BatchJobKind(StrEnum):
	"""What a batch zip job produces: converted outputs, or the stored files unchanged."""

	CONVERT = "convert"
	DOWNLOAD = "download"


@dataclass(slots=True)
class GalleryBatchConvertJob:
	job_id: str
	item_count: int
	phase: ExportJobPhase
	percent: int
	current_index: int
	results: list[BatchConvertItemResult]
	download_path: str
	error: str
	kind: BatchJobKind = BatchJobKind.CONVERT

	def to_dict(self) -> dict[str, object]:
		return {
			"job_id": self.job_id,
			"kind": self.kind.value,
			"phase": self.phase.value,
			"percent": self.percent,
			"item_count": self.item_count,
			"current_index": self.current_index,
			"results": [result.to_dict() for result in self.results],
			"download_url": (
				f"/api/gallery/batch/convert/{self.job_id}/file"
				if self.phase is ExportJobPhase.DONE and self.download_path
				else ""
			),
			"error": self.error,
		}


def normalize_batch_paths(relative_paths: Sequence[str]) -> tuple[str, ...]:
	"""Validate and de-duplicate a client-supplied path list, preserving first-seen order.

	Raises UnsafeBatchPathError for any path failing ``is_safe_gallery_relative_path`` (the whole
	request is rejected) and BatchTooLargeError when more than MAX_GALLERY_BATCH_ITEMS distinct
	paths remain.
	"""
	for path in relative_paths:
		if not is_safe_gallery_relative_path(path):
			raise UnsafeBatchPathError(path)
	distinct = tuple(dict.fromkeys(relative_paths))
	if len(distinct) > MAX_GALLERY_BATCH_ITEMS:
		raise BatchTooLargeError(f"at most {MAX_GALLERY_BATCH_ITEMS} items per batch")
	return distinct


def zip_entry_name(relative_path: str, export_format: ExportFormat | None) -> str:
	"""Entry name for one archive member: converted outputs append ``.jpg`` / ``.mp4`` to the full
	relative path (same injective rule as ``.exports/``); pass-through files keep their relative path.
	"""
	name = relative_path.replace("\\", "/").lstrip("/")
	if export_format is ExportFormat.JPEG:
		return f"{name}.jpg"
	if export_format is ExportFormat.H264_AAC:
		return f"{name}.mp4"
	return name


def _disambiguated(name: str, taken: set[str]) -> str:
	stem, dot, ext = name.rpartition(".")
	if not dot:
		stem, ext = name, ""
	counter = 2
	while True:
		candidate = f"{stem}_{counter}.{ext}" if ext else f"{stem}_{counter}"
		if candidate not in taken:
			return candidate
		counter += 1


def assign_zip_entry_names(results: Sequence[BatchConvertItemResult]) -> tuple[BatchConvertItemResult, ...]:
	"""Return the successful results with unique ``archive_name`` values.

	Built only from validated relative paths (never client-supplied names); no entry contains ``..``
	or an absolute path. Residual collisions (a stored ``x.avif.jpg`` passed through next to a
	converted ``x.avif``) are disambiguated deterministically.
	"""
	taken: set[str] = set()
	named: list[BatchConvertItemResult] = []
	for result in results:
		if result.outcome is BatchConvertOutcome.SKIPPED:
			continue
		name = zip_entry_name(result.relative_path, result.export_format)
		if name in taken:
			name = _disambiguated(name, taken)
		taken.add(name)
		named.append(replace(result, archive_name=name))
	return tuple(named)


def required_free_bytes(reencode_source_sizes: Iterable[int], passthrough_sizes: Iterable[int]) -> int:
	"""Conservative disk estimate: sources that need a re-encode plus pass-through files (zip copy)."""
	return sum(reencode_source_sizes) + sum(passthrough_sizes)


def is_batch_artifact_expired(age_seconds: float) -> bool:
	"""True once a batch job folder under ``.exports/.batch/`` is older than BATCH_ARTIFACT_MAX_AGE_SECONDS."""
	return age_seconds >= BATCH_ARTIFACT_MAX_AGE_SECONDS
