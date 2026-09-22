from __future__ import annotations

from pathlib import Path

from spacemaker.domain.gallery_export import is_safe_gallery_relative_path
from spacemaker.domain.library import LibraryFolder
from spacemaker.ports.outbound.filesystem import FileSystemPort


class DeleteGalleryItem:
	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def run(self, library_root: str, relative_path: str) -> bool:
		if not is_safe_gallery_relative_path(relative_path):
			raise ValueError("invalid path")
		full = self._filesystem.library_path(library_root, LibraryFolder.CONVERTED, relative_path)
		if not self._filesystem.exists(full):
			return False
		self._filesystem.delete_file(full)
		thumb = Path(library_root) / ".thumbnails" / Path(relative_path).with_suffix(".jpg")
		if thumb.is_file():
			self._filesystem.delete_file(str(thumb))
		return True
