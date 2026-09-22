from __future__ import annotations

import os
from pathlib import Path

from adbutils import AdbClient, AdbDevice

from spacemaker.domain.library_paths import skip_media_path
from spacemaker.domain.media import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from spacemaker.ports.outbound.device_repository import DeviceInfo


_MEDIA_ROOTS = (
	"/sdcard/DCIM",
	"/sdcard/Pictures",
	"/sdcard/Movies",
	"/storage/emulated/0/DCIM",
	"/storage/emulated/0/Pictures",
)


class AdbDeviceRepository:
	def __init__(self, adb_path: Path) -> None:
		os.environ["ADBUTILS_ADB_PATH"] = str(adb_path)
		self._client = AdbClient(host="127.0.0.1", port=5037)

	def list_devices(self) -> list[DeviceInfo]:
		out: list[DeviceInfo] = []
		for device in self._client.device_list():
			if device.get_state() != "device":
				continue
			serial = device.serial or "unknown"
			label = device.prop.get("ro.product.model") or serial
			out.append(DeviceInfo(device_id=serial, label=label))
		return out

	def list_media_paths(self, device_id: str) -> list[str]:
		device = self._client.device(device_id)
		allowed = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
		found: set[str] = set()
		for root in _MEDIA_ROOTS:
			output = self._shell_text(device, f"find {root} -type f 2>/dev/null || true")
			for line in output.splitlines():
				path = line.strip()
				if not path or "." not in path or skip_media_path(path):
					continue
				ext = path.rsplit(".", 1)[-1].lower()
				if ext in allowed:
					found.add(path)
		return sorted(found)

	def remote_file_size(self, device_id: str, device_path: str) -> int:
		device = self._client.device(device_id)
		output = self._shell_text(device, f"stat -c %s {device_path} 2>/dev/null || wc -c < {device_path}")
		text = output.strip().splitlines()[-1].strip() if output.strip() else ""
		try:
			return int(text)
		except ValueError:
			return 0

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None:
		Path(local_path).parent.mkdir(parents=True, exist_ok=True)
		device = self._client.device(device_id)
		device.sync.pull(device_path, local_path)

	def delete_device_file(self, device_id: str, device_path: str) -> None:
		device = self._client.device(device_id)
		device.shell(f"rm -f {device_path}")

	@staticmethod
	def _shell_text(device: AdbDevice, command: str) -> str:
		result = device.shell(command)
		if isinstance(result, str):
			return result
		output = getattr(result, "output", None)
		return output if isinstance(output, str) else str(result)
