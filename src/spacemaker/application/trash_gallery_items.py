from __future__ import annotations

from collections.abc import Sequence

from spacemaker.application.gallery_cache_cleanup import delete_gallery_derived_caches
from spacemaker.domain.gallery_batch import (
	TrashError,
	TrashItemResult,
	TrashOutcome,
	normalize_batch_paths,
)
from spacemaker.domain.library import LibraryFolder
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.trash import TrashPort


class TrashGalleryItems:
	"""Inbound use case: move selected ``processed/`` files to the system Trash (never hard-delete).

	Spec: specs/gallery-batch/SPEC.md. The caller (AppServices) removes the matching gallery
	index rows for results whose outcome is TRASHED or ALREADY_GONE, like ``DeleteGalleryItem``.
	"""

	def __init__(self, filesystem: FileSystemPort, trash: TrashPort) -> None:
		self._filesystem = filesystem
		self._trash = trash

	def run(self, library_root: str, relative_paths: Sequence[str]) -> list[TrashItemResult]:
		"""Validate the whole list first (UnsafeBatchPathError / BatchTooLargeError before any file is
		touched), then trash each file independently.

		Per item: TRASHED (file moved, thumbnail + export caches removed), ALREADY_GONE (missing on
		disk; caches cleaned, treated as done), FAILED (TrashError; file left untouched, reason set).
		"""
		paths = normalize_batch_paths(relative_paths)
		results: list[TrashItemResult] = []
		for relative in paths:
			full = self._filesystem.library_path(library_root, LibraryFolder.PROCESSED, relative)
			if not self._filesystem.exists(full):
				delete_gallery_derived_caches(self._filesystem, library_root, relative)
				results.append(TrashItemResult(relative, TrashOutcome.ALREADY_GONE))
				continue
			try:
				self._trash.move_to_trash(full)
			except TrashError as error:
				results.append(TrashItemResult(relative, TrashOutcome.FAILED, str(error) or "could not move to Trash"))
				continue
			delete_gallery_derived_caches(self._filesystem, library_root, relative)
			results.append(TrashItemResult(relative, TrashOutcome.TRASHED))
		return results
