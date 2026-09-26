from __future__ import annotations

from typing import Protocol


class UserPreferencesPort(Protocol):
	"""Disk-backed user preferences that survive app relaunch.

	``get_compress_media`` returns ``None`` when the user has never saved a choice
	(callers apply the domain default via ``resolve_compress_media_preference``).
	"""

	def get_compress_media(self) -> bool | None: ...

	def set_compress_media(self, enabled: bool) -> None: ...
