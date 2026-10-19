from __future__ import annotations

import dataclasses

from spacemaker.application.device_listing_cache import DeviceListingCache
from spacemaker.domain.device_browse import (
	DEFAULT_BROWSE_SORT,
	DeviceBrowseQuery,
	DeviceDirectoryScrollPage,
	decode_sorted_cursor,
	normalize_browse_path,
	scroll_page,
)
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort
from spacemaker.ports.outbound.user_preferences import UserPreferencesPort


class ListDeviceDirectory:
	"""Device file picker use case: validate path, list one directory (cached), filter, keyset-page."""

	def __init__(
		self,
		device_repository: DeviceRepositoryPort,
		*,
		cache: DeviceListingCache | None = None,
		preferences: UserPreferencesPort | None = None,
	) -> None:
		self._devices = device_repository
		self._cache = cache
		self._preferences = preferences

	def scroll(
		self, method_key: str, device_id: str, path: str, request: DeviceBrowseQuery
	) -> DeviceDirectoryScrollPage:
		"""Keyset-paginated, filtered listing.

		Normalizes ``path``, fetches the directory through the cache (``request.refresh`` bypasses it),
		then applies ``scroll_page``. Raises ``DeviceBrowseError`` including ``INVALID_CURSOR``, which is
		raised before any device call when the cursor is bad.

		``request.sort`` ``None`` resolves to the stored picker preference
		(``DEFAULT_BROWSE_SORT`` without ``preferences`` or when unset); the cursor is validated against the
		effective sort before any device call. After a successful listing, an explicit ``request.sort``
		that differs from the stored one is saved; requests without a sort never write.
		"""
		relative = normalize_browse_path(path)
		stored = self._preferences.get_device_picker_sort() if self._preferences is not None else None
		effective = request.sort or stored or DEFAULT_BROWSE_SORT
		if request.cursor is not None:
			decode_sorted_cursor(request.cursor, effective)
		if self._cache is None:
			entries = self._devices.list_directory(device_id, relative)
		else:
			entries = self._cache.get_or_list(
				(method_key, device_id, relative),
				lambda: self._devices.list_directory(device_id, relative),
				refresh=request.refresh,
			)
		page = scroll_page(relative, entries, dataclasses.replace(request, sort=effective))
		if request.sort is not None and self._preferences is not None and request.sort != stored:
			self._preferences.set_device_picker_sort(request.sort)
		return page
