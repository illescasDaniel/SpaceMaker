from __future__ import annotations

from spacemaker.domain.library import LibraryFolder
from spacemaker.ports.outbound.filesystem import FileSystemPort


class ErrorRecovery:
	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def move_all_errors_to_processed(self, library_root: str) -> int:
		error_root = self._filesystem.library_path(library_root, LibraryFolder.ERROR, "")
		files = self._filesystem.list_files_recursive(error_root)
		for rel in files:
			src = self._filesystem.library_path(library_root, LibraryFolder.ERROR, rel)
			dest = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, rel)
			self._filesystem.move_file(src, dest)
		return len(files)
