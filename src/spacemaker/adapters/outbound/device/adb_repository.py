from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import BinaryIO, NoReturn

from adbutils import AdbClient, AdbDevice, AdbError

from spacemaker.adapters.outbound.device.android_listing import (
	android_list_command,
	android_stat_file_command,
	classify_android_shell_failure,
	parse_android_stat_listing,
)
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind, DeviceEntry
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

# Android user-storage aliases, sdcard-style first (picker paths are storage-relative).
_STORAGE_ROOTS = (
	"/storage/self/primary",
	"/storage/emulated/0",
	"/sdcard",
)

_LIST_TIMEOUT_SECONDS = 20.0


class AdbDeviceRepository:
	def __init__(self, adb_path: Path) -> None:
		os.environ["ADBUTILS_ADB_PATH"] = str(adb_path)
		self._adb_path = Path(adb_path)
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
		found: set[str] = set()
		for raw in extras:
			relative = normalize_device_relative_path(raw.lstrip("/"))
			if relative is None:
				continue
			for abs_path in self._absolute_extra_candidates(relative):
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
	def _absolute_extra_candidates(relative: str) -> list[str]:
		rel = relative.lstrip("/")
		lower = rel.lower()
		# Already rooted (e.g. sdcard/WhatsApp/... stored without leading slash).
		for prefix in _STORAGE_ROOTS:
			p = prefix.lstrip("/")
			if lower == p.lower() or lower.startswith(p.lower() + "/"):
				return ["/" + rel.rstrip("/")]
		candidates = [f"{prefix.rstrip('/')}/{rel}".rstrip("/") for prefix in _STORAGE_ROOTS]
		candidates.append("/" + rel.rstrip("/"))
		return list(dict.fromkeys(candidates))

	def list_directory(self, device_id: str, path: str) -> list[DeviceEntry]:
		"""One ``adb shell`` call for one directory under user storage (never recursive)."""
		command = android_list_command(path)
		try:
			device = self._client.device(device_id)
			output = self._shell_text(device, command, timeout=_LIST_TIMEOUT_SECONDS)
		except TimeoutError as exc:
			raise DeviceBrowseError(DeviceBrowseErrorKind.TIMEOUT) from exc
		except AdbError as exc:
			raise DeviceBrowseError(classify_android_shell_failure(str(exc)), str(exc)) from exc
		except OSError as exc:
			raise DeviceBrowseError(DeviceBrowseErrorKind.UNPLUGGED, str(exc)) from exc
		entries = parse_android_stat_listing(output)
		if not entries and output.strip():
			kind = classify_android_shell_failure(output)
			if kind is not DeviceBrowseErrorKind.FAILED or "no such" not in output.lower():
				raise DeviceBrowseError(kind, output.strip())
		return entries

	def stat_file(self, device_id: str, path: str) -> DeviceEntry:
		"""Name, size and mtime of one file under user storage; one ``adb exec-out stat`` call."""
		result = self._run_adb(device_id, android_stat_file_command(path), _LIST_TIMEOUT_SECONDS)
		text = result.stdout.decode("utf-8", errors="replace")
		entries = parse_android_stat_listing(text) if result.returncode == 0 else []
		if not entries:
			kind = classify_android_shell_failure(text + result.stderr.decode("utf-8", errors="replace"))
			raise DeviceBrowseError(DeviceBrowseErrorKind.NOT_FOUND if kind is DeviceBrowseErrorKind.FAILED else kind)
		entry = entries[0]
		return DeviceEntry(path.rsplit("/", 1)[-1], entry.is_dir, entry.size, entry.mtime)

	def read_head(self, device_id: str, path: str, max_bytes: int, timeout_s: float) -> bytes:
		"""First ``max_bytes`` bytes via ``adb exec-out head -c`` (binary-safe; never pulls the whole file)."""
		remote = f"head -c {int(max_bytes)} -- {shlex.quote(self._storage_file_path(path))}"
		result = self._run_adb(device_id, remote, timeout_s)
		if result.returncode != 0:
			self._raise_adb_failure(result)
		return result.stdout

	def read_range(self, device_id: str, path: str, offset: int, length: int, timeout_s: float) -> bytes:
		"""``length`` bytes from ``offset`` via ``adb exec-out dd`` (byte-exact; reads only the range). ``exec-out``
		merges the remote stderr into stdout, so dd must print no summary (``status=none``)."""
		remote = (
			f"dd if={shlex.quote(self._storage_file_path(path))} iflag=skip_bytes,count_bytes "
			f"skip={int(offset)} count={int(length)} status=none"
		)
		result = self._run_adb(device_id, remote, timeout_s)
		if result.returncode != 0:
			self._raise_adb_failure(result)
		return result.stdout

	def pull_file_with_timeout(self, device_id: str, path: str, local_path: str, timeout_s: float) -> None:
		"""Stream a whole file to ``local_path`` via ``adb exec-out cat``; a partial file may remain on failure."""
		remote = f"cat -- {shlex.quote(self._storage_file_path(path))}"
		Path(local_path).parent.mkdir(parents=True, exist_ok=True)
		with open(local_path, "wb") as out:
			result = self._run_adb(device_id, remote, timeout_s, stdout=out)
		if result.returncode != 0:
			self._raise_adb_failure(result)

	@staticmethod
	def _storage_file_path(path: str) -> str:
		"""Absolute device path of a storage-relative, already validated ``path``."""
		return f"/sdcard/{path.lstrip('/')}"

	def _adb_command(self, device_id: str, remote_command: str) -> list[str]:
		return [str(self._adb_path), "-s", device_id, "exec-out", remote_command]

	def _run_adb(
		self, device_id: str, remote_command: str, timeout_s: float, *, stdout: BinaryIO | None = None
	) -> subprocess.CompletedProcess[bytes]:
		try:
			return subprocess.run(  # noqa: S603
				self._adb_command(device_id, remote_command),
				stdout=stdout if stdout is not None else subprocess.PIPE,
				stderr=subprocess.PIPE,
				timeout=timeout_s,
				check=False,
			)
		except subprocess.TimeoutExpired as exc:
			raise DeviceBrowseError(DeviceBrowseErrorKind.TIMEOUT) from exc
		except OSError as exc:
			raise DeviceBrowseError(DeviceBrowseErrorKind.UNPLUGGED, str(exc)) from exc

	@staticmethod
	def _raise_adb_failure(result: subprocess.CompletedProcess[bytes]) -> NoReturn:
		text = (result.stderr or b"").decode("utf-8", errors="replace")
		if not text.strip() and result.stdout:
			text = result.stdout[:400].decode("utf-8", errors="replace")
		kind = classify_android_shell_failure(text)
		if kind is DeviceBrowseErrorKind.FAILED and "no such" in text.lower():
			kind = DeviceBrowseErrorKind.NOT_FOUND
		raise DeviceBrowseError(kind, text.strip())

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

	@staticmethod
	def _shell_text(device: AdbDevice, command: str, *, timeout: float | None = None) -> str:
		result = device.shell(command, timeout=timeout)
		if isinstance(result, str):
			return result
		output = getattr(result, "output", None)
		return output if isinstance(output, str) else str(result)
