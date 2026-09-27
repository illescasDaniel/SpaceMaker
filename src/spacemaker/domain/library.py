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


def gallery_index_path(library_root: str) -> str:
	return str(Path(library_root) / GALLERY_INDEX_FILENAME)
