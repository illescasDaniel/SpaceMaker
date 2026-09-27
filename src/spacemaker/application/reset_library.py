from __future__ import annotations

from pathlib import Path

from spacemaker.domain.library import LIBRARY_FOLDERS, gallery_index_path
from spacemaker.domain.library_paths import EXPORTS_DIR_NAME, THUMBNAILS_DIR_NAME
from spacemaker.ports.outbound.filesystem import FileSystemPort


class ResetLibrary:
	"""Wipe all library buckets and derived caches under the library root."""

	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def run(self, library_root: str) -> None:
		if not library_root:
			raise ValueError("library_root required")
		root = Path(library_root)
		for folder in LIBRARY_FOLDERS:
			self._filesystem.delete_directory(str(root / folder.value))
		self._filesystem.delete_directory(str(root / THUMBNAILS_DIR_NAME))
		self._filesystem.delete_directory(str(root / EXPORTS_DIR_NAME))
		self._filesystem.delete_file(gallery_index_path(library_root))
		for sidecar in (".index.sqlite-wal", ".index.sqlite-shm"):
			self._filesystem.delete_file(str(root / sidecar))
		self._filesystem.ensure_library_folders(library_root)
