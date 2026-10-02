from __future__ import annotations

from typing import Protocol


class ClockPort(Protocol):
	def monotonic(self) -> float:
		"""Seconds from an arbitrary fixed origin; never goes backwards."""
		...
