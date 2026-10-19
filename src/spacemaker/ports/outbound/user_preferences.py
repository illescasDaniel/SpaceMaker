from __future__ import annotations

from typing import Protocol

from spacemaker.domain.device_browse import DeviceBrowseSort


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

	def get_device_picker_sort(self) -> DeviceBrowseSort | None:
		"""Last sort used in the phone picker, or ``None`` when never saved or unreadable (caller applies
		``DEFAULT_BROWSE_SORT``). Stored values are re-validated with ``parse_device_browse_sort``.
		"""
		...

	def set_device_picker_sort(self, sort: DeviceBrowseSort | None) -> None:
		"""Store the picker sort (key ``device_picker_sort``); ``None`` restores the default."""
		...

	def clear(self) -> None:
		"""Remove all saved preferences (defaults apply on next read)."""
		...
