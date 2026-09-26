from __future__ import annotations

import os
import shutil
from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.library_paths import SKIPPED_LIBRARY_DIR_NAMES, skip_media_path
from spacemaker.domain.media import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from spacemaker.ports.outbound.device_repository import DeviceInfo


class MtpDeviceRepository:
	def __init__(self, runner: ToolRunner | None = None) -> None:
		self._runner = runner or ToolRunner()

	def list_devices(self) -> list[DeviceInfo]:
		devices = self._linux_gvfs_devices()
		if devices:
			return devices
		return self._libmtp_detect_devices()

	def list_media_paths(self, device_id: str) -> list[str]:
		mount = Path(device_id)
		if mount.is_dir() and self._is_gvfs_mount(mount):
			return self._walk_media(mount)
		return []

	def list_file_paths(self, device_id: str) -> list[str]:
		mount = Path(device_id)
		if mount.is_dir() and self._is_gvfs_mount(mount):
			return self._walk_files(mount)
		return []

	def remote_file_size(self, device_id: str, device_path: str) -> int:
		mount = Path(device_id)
		if mount.is_dir() and self._is_gvfs_mount(mount):
			full = mount / device_path.lstrip("/")
			if full.is_file():
				return full.stat().st_size
		return 0

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None:
		mount = Path(device_id)
		if mount.is_dir() and self._is_gvfs_mount(mount):
			src = mount / device_path.lstrip("/")
			Path(local_path).parent.mkdir(parents=True, exist_ok=True)
			shutil.copy2(src, local_path)
			return
		try:
			Path(local_path).parent.mkdir(parents=True, exist_ok=True)
			self._runner.run(
				BundledTool.MTP_GETFILE,
				[device_path, local_path],
			)
		except FileNotFoundError as exc:
			raise RuntimeError("MTP getfile tool not available") from exc

	def delete_device_file(self, device_id: str, device_path: str) -> None:
		mount = Path(device_id)
		if mount.is_dir() and self._is_gvfs_mount(mount):
			full = mount / device_path.lstrip("/")
			full.unlink(missing_ok=True)

	def _libmtp_detect_devices(self) -> list[DeviceInfo]:
		try:
			result = self._runner.run(BundledTool.MTP_DETECT, [], check=False)
		except FileNotFoundError:
			return []
		if result.returncode != 0:
			return []
		text = result.stdout.lower()
		if "no raw devices found" in text or "unable to open" in text:
			return []
		name = "MTP device"
		for line in result.stdout.splitlines():
			if "Friendly name:" in line:
				name = line.split("Friendly name:", 1)[1].strip()
				break
		if name == "MTP device" and "friendly name" not in result.stdout.lower():
			return []
		return [DeviceInfo(device_id="libmtp:0", label=name or "Phone (MTP)")]

	def _linux_gvfs_devices(self) -> list[DeviceInfo]:
		if os.name != "posix":
			return []
		uid = os.getuid()
		base = Path(f"/run/user/{uid}/gvfs")
		if not base.is_dir():
			return []
		out: list[DeviceInfo] = []
		for entry in sorted(base.iterdir()):
			if "mtp" not in entry.name.lower():
				continue
			if not self._gvfs_mount_usable(entry):
				continue
			out.append(DeviceInfo(device_id=str(entry.resolve()), label=self._friendly_gvfs_label(entry)))
		return out

	def _gvfs_mount_usable(self, mount: Path) -> bool:
		try:
			os.listdir(mount)
			return True
		except OSError:
			return False

	def _friendly_gvfs_label(self, mount: Path) -> str:
		name = mount.name
		if "]" in name and "[" in name:
			inner = name.split("[", 1)[-1].rsplit("]", 1)[0]
			if inner:
				return inner.replace("%20", " ")
		return name

	def _is_gvfs_mount(self, path: Path) -> bool:
		return "gvfs" in str(path) or "mtp" in path.name.lower()

	def _walk_media(self, root: Path) -> list[str]:
		allowed = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
		return self._walk_paths(root, allowed=allowed)

	def _walk_files(self, root: Path) -> list[str]:
		return self._walk_paths(root, allowed=None)

	def _walk_paths(self, root: Path, *, allowed: frozenset[str] | None) -> list[str]:
		paths: list[str] = []
		for dirpath, dirnames, filenames in os.walk(root):
			dirnames[:] = [name for name in dirnames if name not in SKIPPED_LIBRARY_DIR_NAMES]
			for name in filenames:
				ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
				if allowed is not None and ext not in allowed:
					continue
				full = Path(dirpath) / name
				rel = full.relative_to(root).as_posix()
				if skip_media_path(rel):
					continue
				paths.append(rel)
		return sorted(paths)
