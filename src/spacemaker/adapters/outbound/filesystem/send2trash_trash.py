from __future__ import annotations

from send2trash import send2trash

from spacemaker.domain.gallery_batch import TrashError


class SystemTrash:
	"""Moves files to the operating-system Trash / Recycle Bin. Never hard-deletes."""

	def move_to_trash(self, path: str) -> None:
		try:
			send2trash(path)
		except Exception as error:  # noqa: BLE001 - send2trash raises platform-specific error types
			raise TrashError(str(error) or "could not move to Trash") from error
