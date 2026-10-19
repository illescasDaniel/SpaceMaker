from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from spacemaker.domain.device_browse import DeviceEntry


@dataclass(frozen=True, slots=True)
class DeviceInfo:
	device_id: str
	label: str


class DeviceRepositoryPort(Protocol):
	def list_devices(self) -> list[DeviceInfo]: ...

	def list_media_paths(self, device_id: str) -> list[str]: ...

	def list_file_paths(self, device_id: str) -> list[str]:
		"""All transferable files (any type) for USB file transfer — not media-only."""
		...

	def list_extra_file_paths(self, device_id: str, extras: frozenset[str]) -> list[str]:
		"""Expand Browse extras (mount-relative folders/files) to device file paths."""
		...

	def browse_root(self, device_id: str) -> str | None:
		"""Host filesystem path for Browse / exist-probe, or None if not mount-backed."""
		...

	def list_directory(self, device_id: str, path: str) -> list[DeviceEntry]:
		"""Children of one directory (never recursive); ``path`` is storage-relative, ``""`` = root.

		One device round-trip per call. Raises ``DeviceBrowseError`` (permission denied,
		unauthorized, unplugged, timeout, not found). Order is unspecified — the use case sorts and pages.
		"""
		...

	def remote_file_size(self, device_id: str, device_path: str) -> int: ...

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None: ...

	def delete_device_file(self, device_id: str, device_path: str) -> None: ...
