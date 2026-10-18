from __future__ import annotations

from typing import Protocol


class TrashPort(Protocol):
	"""Outbound: move a file to the operating-system Trash / Recycle Bin.

	The only way the gallery batch feature removes a user file. There is deliberately no
	hard-delete fallback: an implementation that cannot trash a file raises
	``spacemaker.domain.gallery_batch.TrashError`` and leaves the file untouched.
	"""

	def move_to_trash(self, path: str) -> None: ...
