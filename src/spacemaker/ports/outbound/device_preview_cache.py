from __future__ import annotations

from typing import Protocol


class DevicePreviewCachePort(Protocol):
	"""Persistent JPEG cache for device previews (app cache directory, never the library or the phone)."""

	def get(self, key: str) -> bytes | None:
		"""Cached JPEG for ``key`` or ``None``; a hit marks the entry as recently used. No device call."""
		...

	def put(self, key: str, jpeg: bytes) -> None:
		"""Store atomically (temp file + rename), then evict least-recently-used entries until the cache is
		<= ``PREVIEW_CACHE_MAX_BYTES`` (the new entry is always kept).
		"""
		...
