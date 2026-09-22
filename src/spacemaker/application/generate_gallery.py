from __future__ import annotations

from datetime import datetime

from spacemaker.domain.gallery import GalleryItem, MonthGroup, group_timeline
from spacemaker.domain.library import LibraryFolder
from spacemaker.ports.outbound.filesystem import FileSystemPort


class GenerateGallery:
	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def list_timeline(
		self,
		library_root: str,
		*,
		captured_at_for: dict[str, datetime] | None = None,
	) -> list[MonthGroup]:
		converted_root = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, "")
		paths = self._filesystem.list_files_recursive(converted_root)
		fallback = datetime.fromtimestamp(0)
		lookup = captured_at_for or {}
		items = [GalleryItem(relative_path=rel, captured_at=lookup.get(rel, fallback)) for rel in paths]
		return group_timeline(items)
