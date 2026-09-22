from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LibraryFolder(StrEnum):
	ORIGINALS = "originals"
	CONVERTED = "converted"
	ERROR = "error"
	INVALID = "invalid"


LIBRARY_FOLDERS: tuple[LibraryFolder, ...] = (
	LibraryFolder.ORIGINALS,
	LibraryFolder.CONVERTED,
	LibraryFolder.ERROR,
	LibraryFolder.INVALID,
)


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
