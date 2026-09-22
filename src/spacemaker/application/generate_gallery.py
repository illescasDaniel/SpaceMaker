from __future__ import annotations

from datetime import datetime

from spacemaker.domain.gallery import (
	GalleryItem,
	MonthGroup,
	days_in_month,
	gallery_item,
	group_timeline,
	items_for_day,
)
from spacemaker.domain.library import LibraryFolder
from spacemaker.ports.outbound.filesystem import FileSystemPort


class GenerateGallery:
	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def list_items(
		self,
		library_root: str,
		*,
		captured_at_for: dict[str, datetime] | None = None,
	) -> list[GalleryItem]:
		converted_root = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, "")
		paths = self._filesystem.list_files_recursive(converted_root)
		fallback = datetime.fromtimestamp(0)
		lookup = captured_at_for or {}
		return [gallery_item(relative_path=rel, captured_at=lookup.get(rel, fallback)) for rel in paths]

	def list_timeline(
		self,
		library_root: str,
		*,
		captured_at_for: dict[str, datetime] | None = None,
	) -> list[MonthGroup]:
		return group_timeline(self.list_items(library_root, captured_at_for=captured_at_for))

	def calendar_days(
		self,
		library_root: str,
		year: int,
		month: int,
		*,
		captured_at_for: dict[str, datetime] | None = None,
	) -> list[int]:
		items = self.list_items(library_root, captured_at_for=captured_at_for)
		return sorted(days_in_month(items, year, month))

	def list_day(
		self,
		library_root: str,
		year: int,
		month: int,
		day: int,
		*,
		captured_at_for: dict[str, datetime] | None = None,
	) -> list[GalleryItem]:
		items = self.list_items(library_root, captured_at_for=captured_at_for)
		return items_for_day(items, year, month, day)
