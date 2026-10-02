from __future__ import annotations

import contextlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from adbutils import AdbClient, AdbDevice

from spacemaker.adapters.outbound.device.mount_dirs import remove_empty_mount_dir
from spacemaker.domain.library_paths import skip_media_path
from spacemaker.domain.media import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from spacemaker.domain.transfer_folders import TransferFolder, existing_transfer_folders_from_dir_names
from spacemaker.ports.outbound.device_repository import DeviceInfo


_MEDIA_ROOTS = (
	"/sdcard/DCIM",
	"/sdcard/Pictures",
	"/sdcard/Movies",
	"/storage/emulated/0/DCIM",
	"/storage/emulated/0/Pictures",
)

_FILE_ROOTS = (
	"/sdcard/Download",
	"/sdcard/Documents",
	"/sdcard/DCIM",
	"/sdcard/Pictures",
	"/sdcard/Movies",
	"/sdcard/Music",
	"/storage/emulated/0/Download",
	"/storage/emulated/0/Documents",
	"/storage/emulated/0/DCIM",
	"/storage/emulated/0/Pictures",
	"/storage/emulated/0/Movies",
	"/storage/emulated/0/Music",
)

# Prefer sdcard-style roots so Browse shows Download/DCIM near the top.
_ADBFS_SUBDIRS = (
	"/storage/self/primary",
	"/storage/emulated/0",
	"/sdcard",
)

_SHELL_PRESET_PATHS: dict[TransferFolder, tuple[str, ...]] = {
	TransferFolder.DOWNLOAD: ("/sdcard/Download", "/storage/emulated/0/Download"),
	TransferFolder.DOCUMENTS: ("/sdcard/Documents", "/storage/emulated/0/Documents"),
	TransferFolder.DCIM: ("/sdcard/DCIM", "/storage/emulated/0/DCIM"),
	TransferFolder.PICTURES: ("/sdcard/Pictures", "/storage/emulated/0/Pictures"),
	TransferFolder.MOVIES: ("/sdcard/Movies", "/storage/emulated/0/Movies"),
	TransferFolder.MUSIC: ("/sdcard/Music", "/storage/emulated/0/Music"),
}

_ADBFS_TIMEOUT_SECONDS = 8.0
_ORPHAN_MOUNT_PREFIX = "spacemaker-adbfs-"


class AdbDeviceRepository:
	def __init__(
		self,
		adb_path: Path,
		*,
		which: Callable[[str], str | None] | None = None,
		run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
		test_mounts: dict[str, Path] | None = None,
	) -> None:
		os.environ["ADBUTILS_ADB_PATH"] = str(adb_path)
		self._adb_path = Path(adb_path)
		self._client = AdbClient(host="127.0.0.1", port=5037)
		self._which = which or shutil.which
		self._run = run or subprocess.run
		self._test_mounts = test_mounts
		self._live_mounts: dict[str, Path] = {}
		self._mount_device_roots: dict[str, str] = {}

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
			output = self._shell_text(device, f"find {shlex.quote(root)} -type f 2>/dev/null || true")
			for line in output.splitlines():
				path = line.strip()
				if not path or "." not in path or skip_media_path(path):
					continue
				ext = path.rsplit(".", 1)[-1].lower()
				if ext in allowed:
					found.add(path)
		return sorted(found)

	def list_file_paths(self, device_id: str) -> list[str]:
		device = self._client.device(device_id)
		found: set[str] = set()
		for root in _FILE_ROOTS:
			output = self._shell_text(device, f"find {shlex.quote(root)} -type f 2>/dev/null || true")
			for line in output.splitlines():
				path = line.strip()
				if not path or skip_media_path(path):
					continue
				found.add(path)
		return sorted(found)

	def list_extra_file_paths(self, device_id: str, extras: frozenset[str]) -> list[str]:
		"""Resolve Browse extras (mount-relative) to absolute device file paths via adb."""
		from spacemaker.domain.transfer_folders import normalize_device_relative_path

		device = self._client.device(device_id)
		preferred = self._mount_device_roots.get(device_id)
		found: set[str] = set()
		for raw in extras:
			relative = normalize_device_relative_path(raw.lstrip("/"))
			if relative is None:
				continue
			for abs_path in self._absolute_extra_candidates(relative, preferred):
				kind = self._shell_text(
					device,
					f"if [ -f {shlex.quote(abs_path)} ]; then echo file; "
					f"elif [ -d {shlex.quote(abs_path)} ]; then echo dir; else echo missing; fi",
				).strip()
				if kind == "file":
					if not skip_media_path(abs_path):
						found.add(abs_path)
					break
				if kind == "dir":
					output = self._shell_text(
						device,
						f"find {shlex.quote(abs_path)} -type f 2>/dev/null || true",
					)
					for line in output.splitlines():
						path = line.strip()
						if path and not skip_media_path(path):
							found.add(path)
					break
		return sorted(found)

	@staticmethod
	def _absolute_extra_candidates(relative: str, preferred_root: str | None) -> list[str]:
		rel = relative.lstrip("/")
		candidates: list[str] = []
		seen: set[str] = set()

		def add(path: str) -> None:
			key = path.rstrip("/") or "/"
			if key not in seen:
				seen.add(key)
				candidates.append(key)

		# Already rooted (e.g. sdcard/WhatsApp/... stored without leading slash).
		lower = rel.lower()
		for prefix in _ADBFS_SUBDIRS:
			p = prefix.lstrip("/")
			if lower == p.lower() or lower.startswith(p.lower() + "/"):
				add("/" + rel)
				return candidates
		if preferred_root:
			add(f"{preferred_root.rstrip('/')}/{rel}")
		for prefix in _ADBFS_SUBDIRS:
			add(f"{prefix.rstrip('/')}/{rel}")
		add("/" + rel)
		return candidates

	def browse_backend_available(self) -> bool:
		"""True when adbfs is on PATH (Linux) or a test mount is configured."""
		if self._test_mounts is not None:
			return True
		if sys.platform != "linux":
			return False
		return self._which("adbfs") is not None

	def peek_browse_root(self, device_id: str) -> str | None:
		"""Return an existing session mount without starting adbfs."""
		if self._test_mounts is not None:
			mount = self._test_mounts.get(device_id)
			return str(mount.resolve()) if mount is not None and mount.is_dir() else None
		existing = self._live_mounts.get(device_id)
		if existing is not None and existing.is_dir():
			try:
				os.listdir(existing)
				return str(existing.resolve())
			except OSError:
				self._unmount_path(existing)
				self._live_mounts.pop(device_id, None)
		return None

	def browse_root(self, device_id: str) -> str | None:
		"""Host FUSE mount via adbfs (Linux). Returns None if adbfs unavailable."""
		peeked = self.peek_browse_root(device_id)
		if peeked is not None:
			return peeked
		if self._test_mounts is not None:
			return None
		if sys.platform != "linux":
			return None
		adbfs = self._which("adbfs")
		if not adbfs:
			return None
		self.cleanup_orphan_mounts()
		mount_dir = Path(tempfile.mkdtemp(prefix=_ORPHAN_MOUNT_PREFIX))
		env = os.environ.copy()
		env["ANDROID_SERIAL"] = device_id
		env["ADBUTILS_ADB_PATH"] = str(self._adb_path)
		# Prefer our managed adb on PATH for the adbfs child process.
		adb_dir = str(self._adb_path.parent)
		env["PATH"] = f"{adb_dir}{os.pathsep}{env.get('PATH', '')}"
		mounted = False
		used_subdir: str | None = None
		for subdir in (*_ADBFS_SUBDIRS, None):
			cmd = [adbfs, str(mount_dir)]
			if subdir:
				cmd.extend(["-o", "modules=subdir", "-o", f"subdir={subdir}"])
			try:
				result = self._run(  # noqa: S603
					cmd,
					capture_output=True,
					text=True,
					check=False,
					env=env,
					timeout=_ADBFS_TIMEOUT_SECONDS,
				)
			except subprocess.TimeoutExpired:
				self._unmount_path(mount_dir)
				mount_dir = Path(tempfile.mkdtemp(prefix=_ORPHAN_MOUNT_PREFIX))
				continue
			if result.returncode == 0:
				try:
					os.listdir(mount_dir)
					mounted = True
					used_subdir = subdir
					break
				except OSError:
					self._unmount_path(mount_dir)
					mount_dir = Path(tempfile.mkdtemp(prefix=_ORPHAN_MOUNT_PREFIX))
					continue
			self._unmount_path(mount_dir)
			mount_dir = Path(tempfile.mkdtemp(prefix=_ORPHAN_MOUNT_PREFIX))
		if not mounted:
			remove_empty_mount_dir(mount_dir)
			return None
		self._live_mounts[device_id] = mount_dir
		if used_subdir:
			self._mount_device_roots[device_id] = used_subdir
		else:
			self._mount_device_roots.pop(device_id, None)
		return str(mount_dir.resolve())

	def cleanup_orphan_mounts(self) -> None:
		"""Unmount leftover /tmp/spacemaker-adbfs-* dirs from a prior crashed process."""
		if self._test_mounts is not None or sys.platform != "linux":
			return
		tmp = Path(tempfile.gettempdir())
		for mount in tmp.glob(f"{_ORPHAN_MOUNT_PREFIX}*"):
			if not mount.is_dir():
				continue
			if mount in self._live_mounts.values():
				continue
			self._unmount_path(mount)

	def probe_existing_transfer_folders(self, device_id: str) -> frozenset[TransferFolder]:
		"""Exist-probe via adb shell when FUSE mount is unavailable."""
		device = self._client.device(device_id)
		names: set[str] = set()
		for paths in _SHELL_PRESET_PATHS.values():
			for path in paths:
				output = self._shell_text(device, f"test -d {shlex.quote(path)} && echo yes || true")
				if "yes" in output:
					names.add(Path(path).name)
					break
		return existing_transfer_folders_from_dir_names(names)

	def remote_file_size(self, device_id: str, device_path: str) -> int:
		device = self._client.device(device_id)
		output = self._shell_text(
			device, f"stat -c %s {shlex.quote(device_path)} 2>/dev/null || wc -c < {shlex.quote(device_path)}"
		)
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
		device.shell(f"rm -f {shlex.quote(device_path)}")

	def release_mounts(self) -> None:
		if self._test_mounts is not None:
			self._live_mounts.clear()
			self._mount_device_roots.clear()
			return
		for mount in list(self._live_mounts.values()):
			self._unmount_path(mount)
		self._live_mounts.clear()
		self._mount_device_roots.clear()

	def _unmount_path(self, mount: Path) -> None:
		for name in ("fusermount3", "fusermount", "umount"):
			binary = self._which(name)
			if binary is None:
				continue
			with contextlib.suppress(subprocess.TimeoutExpired):
				self._run(  # noqa: S603
					[binary, "-u", str(mount)],
					capture_output=True,
					text=True,
					check=False,
					timeout=5.0,
				)
			break
		remove_empty_mount_dir(mount)

	def __del__(self) -> None:
		with_context = getattr(self, "_test_mounts", None)
		if with_context is not None:
			return
		with contextlib.suppress(Exception):
			self.release_mounts()

	@staticmethod
	def _shell_text(device: AdbDevice, command: str) -> str:
		result = device.shell(command)
		if isinstance(result, str):
			return result
		output = getattr(result, "output", None)
		return output if isinstance(output, str) else str(result)
