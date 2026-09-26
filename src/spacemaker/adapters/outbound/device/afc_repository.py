from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from spacemaker.adapters.outbound.media.tool_runner import ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool
from spacemaker.domain.library_paths import SKIPPED_LIBRARY_DIR_NAMES, skip_media_path
from spacemaker.domain.media import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from spacemaker.ports.outbound.device_repository import DeviceInfo


_USBMUXD_SOCKETS = (Path("/run/usbmuxd"), Path("/var/run/usbmuxd"))
_AFC_TOP_DIRS = ("DCIM", "Pictures", "Movies")


def usbmuxd_running() -> bool:
	return any(path.exists() for path in _USBMUXD_SOCKETS)


def apple_usb_plugged() -> bool:
	try:
		result = subprocess.run(  # noqa: S603
			["lsusb"],
			capture_output=True,
			text=True,
			check=False,
			timeout=5,
		)
	except (FileNotFoundError, subprocess.TimeoutExpired):
		return False
	text = result.stdout.lower()
	return " 05ac:" in text or "id 05ac" in text


class AfcDeviceRepository:
	def __init__(
		self,
		runner: ToolRunner | None = None,
		*,
		test_mounts: dict[str, Path] | None = None,
	) -> None:
		self._runner = runner or ToolRunner()
		self._test_mounts = test_mounts
		self._live_mounts: dict[str, Path] = {}

	def list_devices(self) -> list[DeviceInfo]:
		if sys.platform != "linux":
			return []
		if not usbmuxd_running():
			raise RuntimeError(
				"usbmuxd is not running — install the usbmuxd package, plug in and unlock the iPhone "
				"(Arch/CachyOS starts the daemon via udev; no systemctl enable). "
				"If the socket is still missing, try: systemctl start usbmuxd",
			)
		self._require_tool(BundledTool.IDEVICE_ID)
		result = self._runner.run(BundledTool.IDEVICE_ID, ["-l"], check=False)
		if result.returncode != 0:
			detail = (result.stderr or result.stdout or "idevice_id failed").strip()
			raise RuntimeError(detail)
		udids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
		out: list[DeviceInfo] = []
		for udid in udids:
			label = self._device_label(udid) or "iPhone"
			out.append(DeviceInfo(device_id=udid, label=label))
		if not out and apple_usb_plugged():
			raise RuntimeError(
				"iPhone is on USB but not paired with usbmux — unlock the phone, tap Trust This Computer, "
				"then unplug and replug. If Trust never appears: Settings → General → Transfer or Reset → "
				"Reset → Reset Location & Privacy. While replugging, run: journalctl -u usbmuxd -f",
			)
		return out

	def list_media_paths(self, device_id: str) -> list[str]:
		mount = self._mount_path(device_id)
		return self._walk_media(mount)

	def list_file_paths(self, device_id: str) -> list[str]:
		_ = device_id
		raise NotImplementedError("USB file transfer listing — implement in Phase 4")

	def remote_file_size(self, device_id: str, device_path: str) -> int:
		mount = self._mount_path(device_id)
		full = mount / device_path.lstrip("/")
		if full.is_file():
			return full.stat().st_size
		return 0

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None:
		mount = self._mount_path(device_id)
		src = mount / device_path.lstrip("/")
		Path(local_path).parent.mkdir(parents=True, exist_ok=True)
		shutil.copy2(src, local_path)

	def delete_device_file(self, device_id: str, device_path: str) -> None:
		mount = self._mount_path(device_id)
		full = mount / device_path.lstrip("/")
		full.unlink(missing_ok=True)

	def _device_label(self, udid: str) -> str:
		try:
			self._require_tool(BundledTool.IDEVICE_INFO)
			result = self._runner.run(
				BundledTool.IDEVICE_INFO,
				["-u", udid, "-k", "DeviceName"],
				check=False,
			)
		except FileNotFoundError:
			return ""
		name = result.stdout.strip()
		return name if result.returncode == 0 else ""

	def _mount_path(self, device_id: str) -> Path:
		if self._test_mounts is not None:
			mount = self._test_mounts.get(device_id)
			if mount is None or not mount.is_dir():
				raise RuntimeError(f"No test mount for device {device_id}")
			return mount
		existing = self._live_mounts.get(device_id)
		if existing is not None and existing.is_dir():
			try:
				os.listdir(existing)
				return existing
			except OSError:
				self._unmount_path(existing)
				self._live_mounts.pop(device_id, None)
		mount_dir = Path(tempfile.mkdtemp(prefix="spacemaker-afc-"))
		self._require_tool(BundledTool.IFUSE)
		ifuse = self._runner.path(BundledTool.IFUSE)
		result = subprocess.run(  # noqa: S603
			[str(ifuse), str(mount_dir), "-u", device_id],
			capture_output=True,
			text=True,
			check=False,
		)
		if result.returncode != 0:
			shutil.rmtree(mount_dir, ignore_errors=True)
			detail = (result.stderr or result.stdout or "").strip()
			raise RuntimeError(detail or "ifuse failed — unlock iPhone and tap Trust")
		self._live_mounts[device_id] = mount_dir
		return mount_dir

	def _walk_media(self, root: Path) -> list[str]:
		allowed = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
		paths: list[str] = []
		scanned_top = False
		for top_name in _AFC_TOP_DIRS:
			sub = root / top_name
			if not sub.is_dir():
				continue
			scanned_top = True
			paths.extend(self._walk_subtree(sub, root, allowed))
		if not scanned_top and self._looks_like_dcim_root(root):
			paths.extend(self._walk_subtree(root, root, allowed))
			paths = [self._ensure_dcim_prefix(rel) for rel in paths]
		return sorted(set(paths))

	def _walk_subtree(self, tree_root: Path, path_base: Path, allowed: frozenset[str]) -> list[str]:
		paths: list[str] = []
		for dirpath, dirnames, filenames in os.walk(tree_root, followlinks=False):
			dirnames[:] = [name for name in dirnames if name not in SKIPPED_LIBRARY_DIR_NAMES]
			for name in filenames:
				ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
				if ext not in allowed:
					continue
				full = Path(dirpath) / name
				rel = full.relative_to(path_base).as_posix()
				if skip_media_path(rel):
					continue
				paths.append(rel)
		return paths

	@staticmethod
	def _looks_like_dcim_root(root: Path) -> bool:
		try:
			for entry in root.iterdir():
				if entry.is_dir() and entry.name.startswith("100APP"):
					return True
		except OSError:
			return False
		return False

	@staticmethod
	def _ensure_dcim_prefix(relative: str) -> str:
		parts = relative.lower().split("/")
		if "dcim" in parts:
			return relative
		return f"DCIM/{relative}"

	def _require_tool(self, tool: BundledTool) -> None:
		self._runner.path(tool)

	def _unmount_path(self, mount: Path) -> None:
		for name in ("fusermount3", "fusermount", "umount"):
			binary = shutil.which(name)
			if binary is None:
				continue
			subprocess.run(  # noqa: S603
				[binary, "-u", str(mount)],
				capture_output=True,
				text=True,
				check=False,
			)
			break
		shutil.rmtree(mount, ignore_errors=True)

	def __del__(self) -> None:
		if self._test_mounts is not None:
			return
		for mount in list(self._live_mounts.values()):
			self._unmount_path(mount)
		self._live_mounts.clear()
