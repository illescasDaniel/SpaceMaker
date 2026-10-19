from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable

from spacemaker.domain.device_browse import DeviceEntry
from spacemaker.ports.outbound.clock import ClockPort


ListingKey = tuple[str, str, str]
"""``(method value, device_id, path)``."""


class DeviceListingCache:
	"""Short-lived, bounded cache of raw directory listings.

	Entries expire ``ttl_seconds`` after being loaded (measured with ``clock.monotonic``); at most
	``max_directories`` listings are kept, evicting the least recently used. Loader exceptions
	propagate and are never cached. Thread-safe (listings run from FastAPI's threadpool).
	"""

	def __init__(self, clock: ClockPort, *, ttl_seconds: float = 30.0, max_directories: int = 8) -> None:
		self._clock = clock
		self._ttl_seconds = ttl_seconds
		self._max_directories = max_directories
		self._lock = threading.Lock()
		self._items: OrderedDict[ListingKey, tuple[float, tuple[DeviceEntry, ...]]] = OrderedDict()

	def get_or_list(
		self, key: ListingKey, loader: Callable[[], list[DeviceEntry]], *, refresh: bool = False
	) -> list[DeviceEntry]:
		"""Return the cached listing for ``key`` or call ``loader``; ``refresh`` forces a reload."""
		with self._lock:
			if not refresh:
				hit = self._items.get(key)
				if hit is not None and self._clock.monotonic() - hit[0] < self._ttl_seconds:
					self._items.move_to_end(key)
					return list(hit[1])
		# Loaded outside the lock: a slow device call must not block other directories.
		loaded = tuple(loader())
		with self._lock:
			self._items[key] = (self._clock.monotonic(), loaded)
			self._items.move_to_end(key)
			while len(self._items) > self._max_directories:
				self._items.popitem(last=False)
		return list(loaded)

	def clear(self) -> None:
		"""Drop every cached listing."""
		with self._lock:
			self._items.clear()
