from __future__ import annotations

from spacemaker.domain.library import JobProgress, LibraryFolder
from spacemaker.ports.outbound.filesystem import FileSystemPort


class PromoteOriginalsToProcessed:
	"""Move every file in originals/ into processed/ as-is (no re-encode)."""

	def __init__(self, filesystem: FileSystemPort) -> None:
		self._filesystem = filesystem

	def run(self, library_root: str) -> JobProgress:
		self._filesystem.ensure_library_folders(library_root)
		rel_paths = self._filesystem.list_files_in_library_folder(library_root, LibraryFolder.ORIGINALS)
		total = len(rel_paths)
		completed = 0
		for relative in rel_paths:
			source = self._filesystem.library_path(library_root, LibraryFolder.ORIGINALS, relative)
			dest = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative)
			self._filesystem.move_file(source, dest)
			completed += 1
		return JobProgress(completed=completed, total=total)
