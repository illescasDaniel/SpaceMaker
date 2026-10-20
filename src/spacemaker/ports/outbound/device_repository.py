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
		"""Expand picker extras (storage-relative folders/files) to device file paths."""
		...

	def list_directory(self, device_id: str, path: str) -> list[DeviceEntry]:
		"""Children of one directory (never recursive); ``path`` is storage-relative, ``""`` = root.

		One device round-trip per call. Raises ``DeviceBrowseError`` (permission denied,
		unauthorized, unplugged, timeout, not found). Order is unspecified — the use case sorts and pages.
		"""
		...

	def stat_file(self, device_id: str, path: str) -> DeviceEntry:
		"""Name, size and mtime of one file; ``path`` is storage-relative like ``list_directory``.

		One device round-trip. Raises ``DeviceBrowseError`` (unplugged, unauthorized, timeout, not found).
		"""
		...

	def read_head(self, device_id: str, path: str, max_bytes: int, timeout_s: float) -> bytes:
		"""First ``max_bytes`` bytes of a file (fewer if shorter); ``path`` is storage-relative.

		One device round-trip, never pulls the whole file. Raises ``DeviceBrowseError`` (unplugged,
		unauthorized, timeout, not found).
		"""
		...

	def read_range(self, device_id: str, path: str, offset: int, length: int, timeout_s: float) -> bytes:
		"""Up to ``length`` bytes starting at ``offset`` (fewer at the end of the file); ``path`` is
		storage-relative. One device round-trip, never reads outside the range. Raises ``DeviceBrowseError``
		(unplugged, unauthorized, timeout, not found) like ``read_head``.
		"""
		...

	def pull_file_with_timeout(self, device_id: str, path: str, local_path: str, timeout_s: float) -> None:
		"""Copy a whole file to ``local_path``; ``path`` is storage-relative, unlike ``pull_file`` whose
		``device_path`` is an absolute device path from ``list_*_paths``.

		One device round-trip. Raises ``DeviceBrowseError`` (unplugged, unauthorized, timeout, not found);
		a partial ``local_path`` may be left behind on failure (the caller deletes it).
		"""
		...

	def remote_file_size(self, device_id: str, device_path: str) -> int: ...

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None: ...

	def delete_device_file(self, device_id: str, device_path: str) -> None: ...
