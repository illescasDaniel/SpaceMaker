from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DeviceInfo:
	device_id: str
	label: str


class DeviceRepositoryPort(Protocol):
	def list_devices(self) -> list[DeviceInfo]: ...

	def list_media_paths(self, device_id: str) -> list[str]: ...

	def remote_file_size(self, device_id: str, device_path: str) -> int: ...

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None: ...

	def delete_device_file(self, device_id: str, device_path: str) -> None: ...
