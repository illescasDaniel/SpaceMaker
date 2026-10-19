from __future__ import annotations

from typing import Protocol


class UserPreferencesPort(Protocol):
	"""Disk-backed user preferences that survive app relaunch.

	``get_compress_media`` returns ``None`` when the user has never saved a choice
	(callers apply the domain default via ``resolve_compress_media_preference``).
	"""

	def get_compress_media(self) -> bool | None: ...

	def set_compress_media(self, enabled: bool) -> None: ...

	def get_usb_transfer_destination(self) -> str | None:
		"""Absolute folder chosen for USB file transfer, or ``None`` for the default."""
		...

	def set_usb_transfer_destination(self, path: str | None) -> None:
		"""Store the chosen destination; ``None`` (or empty) restores the default."""
		...

	def clear(self) -> None:
		"""Remove all saved preferences (defaults apply on next read)."""
		...
