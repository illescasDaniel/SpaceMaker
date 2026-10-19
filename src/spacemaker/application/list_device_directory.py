from __future__ import annotations

from spacemaker.application.device_listing_cache import DeviceListingCache
from spacemaker.domain.device_browse import (
	DeviceBrowseQuery,
	DeviceDirectoryScrollPage,
	decode_browse_cursor,
	normalize_browse_path,
	scroll_page,
)
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort


class ListDeviceDirectory:
	"""Device file picker use case: validate path, list one directory (cached), filter, keyset-page."""

	def __init__(self, device_repository: DeviceRepositoryPort, *, cache: DeviceListingCache | None = None) -> None:
		self._devices = device_repository
		self._cache = cache

	def scroll(
		self, method_key: str, device_id: str, path: str, request: DeviceBrowseQuery
	) -> DeviceDirectoryScrollPage:
		"""Keyset-paginated, filtered listing.

		Normalizes ``path``, fetches the directory through the cache (``request.refresh`` bypasses it),
		then applies ``scroll_page``. Raises ``DeviceBrowseError`` including ``INVALID_CURSOR``, which is
		raised before any device call when the cursor is bad.
		"""
		relative = normalize_browse_path(path)
		if request.cursor is not None:
			decode_browse_cursor(request.cursor)
		if self._cache is None:
			entries = self._devices.list_directory(device_id, relative)
		else:
			entries = self._cache.get_or_list(
				(method_key, device_id, relative),
				lambda: self._devices.list_directory(device_id, relative),
				refresh=request.refresh,
			)
		return scroll_page(relative, entries, request)
