from __future__ import annotations

from typing import Protocol


class DiskSpacePort(Protocol):
	def free_bytes(self, path: str) -> int:
		"""Free space on the volume holding ``path`` (nearest existing ancestor if it does not exist yet)."""
		...
