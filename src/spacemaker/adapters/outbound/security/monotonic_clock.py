from __future__ import annotations

import time


class MonotonicClock:
	def monotonic(self) -> float:
		return time.monotonic()
