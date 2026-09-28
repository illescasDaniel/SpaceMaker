from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class LibraryFolder(StrEnum):
	ORIGINALS = "originals"
	PROCESSED = "processed"
	ERROR = "error"
	INVALID = "invalid"


LIBRARY_FOLDERS: tuple[LibraryFolder, ...] = (
	LibraryFolder.ORIGINALS,
	LibraryFolder.PROCESSED,
	LibraryFolder.ERROR,
	LibraryFolder.INVALID,
)

# Pre-rename on-disk gallery bucket; migrated to LibraryFolder.PROCESSED on ensure.
LEGACY_CONVERTED_FOLDER_NAME = "converted"

GALLERY_INDEX_FILENAME = ".index.sqlite"


class TransferMode(StrEnum):
	COPY = "copy"
	MOVE = "move"


@dataclass(frozen=True, slots=True)
class JobProgress:
	completed: int
	total: int

	@property
	def percent(self) -> int:
		if self.total <= 0:
			return 0
		return min(100, int(100 * self.completed / self.total))


def live_job_progress(completed: int, originals_remaining: int) -> JobProgress:
	"""Progress whose total grows as more files land while a job is running.

	Easy concurrent convert uses ``total = completed + originals_remaining`` so
	the UI stays accurate when Wi‑Fi uploads arrive mid-pass (the file currently
	encoding still counts in ``originals/``).
	"""
	safe_completed = max(0, completed)
	safe_remaining = max(0, originals_remaining)
	return JobProgress(completed=safe_completed, total=safe_completed + safe_remaining)


def gallery_index_path(library_root: str) -> str:
	return str(Path(library_root) / GALLERY_INDEX_FILENAME)
