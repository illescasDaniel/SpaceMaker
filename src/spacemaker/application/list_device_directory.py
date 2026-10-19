from __future__ import annotations

from spacemaker.domain.device_browse import BROWSE_PAGE_SIZE, DeviceDirectoryPage, normalize_browse_path, page_entries
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort


class ListDeviceDirectory:
	"""Device file picker use case: validate path, list one directory, sort, page."""

	def __init__(self, device_repository: DeviceRepositoryPort) -> None:
		self._devices = device_repository

	def execute(self, device_id: str, path: str, cursor: int = 0, limit: int = BROWSE_PAGE_SIZE) -> DeviceDirectoryPage:
		"""Raises ``DeviceBrowseError`` (invalid path, permission denied, unauthorized, unplugged, …)."""
		relative = normalize_browse_path(path)
		entries = self._devices.list_directory(device_id, relative)
		return page_entries(relative, entries, cursor, limit)
