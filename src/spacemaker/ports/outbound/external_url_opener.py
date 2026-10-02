from __future__ import annotations

from typing import Protocol


class ExternalUrlOpenerPort(Protocol):
	def open(self, url: str) -> bool:
		"""Open ``url`` in the user's system browser. False when it could not be launched."""
		...
