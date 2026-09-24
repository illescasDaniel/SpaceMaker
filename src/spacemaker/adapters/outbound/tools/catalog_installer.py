from __future__ import annotations

import hashlib
import io
import shutil
import stat
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import httpx

from spacemaker.adapters.outbound.tools.catalog import load_platform_catalog
from spacemaker.bootstrap.bundled_tools import BundledTool, bundled_tool_path
from spacemaker.bootstrap.paths import managed_tools_dir
from spacemaker.bootstrap.platform import platform_catalog_key
from spacemaker.ports.outbound.tool_installer import ToolInstallResult


class CatalogToolInstaller:
	def __init__(
		self,
		*,
		repo_root: Path,
		dest_dir: Path | None = None,
		platform_key: str | None = None,
		platform_is_windows: bool | None = None,
	) -> None:
		self._repo_root = repo_root
		self._dest = dest_dir or managed_tools_dir()
		self._platform_key = platform_key or platform_catalog_key()
		if platform_is_windows is None:
			platform_is_windows = sys.platform == "win32"
		self._windows = platform_is_windows
		self._catalog = load_platform_catalog(repo_root=repo_root, platform_key=self._platform_key)

	def has_catalog_entry(self, tool_id: str) -> bool:
		entry = self._catalog.get(tool_id)
		if not entry:
			return False
		if entry.get("companion_of"):
			return False
		return bool(entry.get("strategy"))

	def catalog_covers(self, tool_id: str) -> bool:
		entry = self._catalog.get(tool_id)
		if not entry:
			return False
		if entry.get("companion_of"):
			return self.has_catalog_entry(str(entry["companion_of"]))
		return self.has_catalog_entry(tool_id)

	def install(self, tool_id: str) -> ToolInstallResult:
		self._dest.mkdir(parents=True, exist_ok=True)
		entry = self._catalog.get(tool_id)
		if not entry:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="No portable download for this OS")
		if entry.get("companion_of"):
			companion = str(entry["companion_of"])
			primary = self.install(companion)
			if not primary.ok:
				return ToolInstallResult(tool_id=tool_id, ok=False, message=primary.message)
			return ToolInstallResult(tool_id=tool_id, ok=True, message="Installed with " + companion)
		strategy = str(entry.get("strategy", ""))
		try:
			if strategy == "zip":
				return self._install_archive(tool_id, entry, kind="zip")
			if strategy == "zip_flatten":
				return self._install_zip_flatten(tool_id, entry)
			if strategy == "archive":
				return self._install_archive(tool_id, entry, kind="tar")
			if strategy == "file":
				return self._install_file(tool_id, entry)
			if strategy == "static_ffmpeg_wheel":
				return self._install_static_ffmpeg_wheel(entry)
			return ToolInstallResult(tool_id=tool_id, ok=False, message=f"Unknown strategy: {strategy}")
		except Exception as exc:
			return ToolInstallResult(tool_id=tool_id, ok=False, message=str(exc) or exc.__class__.__name__)

	def _install_file(self, tool_id: str, entry: dict[str, Any]) -> ToolInstallResult:
		url = str(entry.get("url", ""))
		if not url:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Missing download URL")
		data = self._download_bytes(url)
		if not self._checksum_ok(data, entry):
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Checksum mismatch")
		dest = bundled_tool_path(BundledTool(tool_id), root=self._dest, platform_is_windows=self._windows)
		dest.write_bytes(data)
		self._make_executable(dest)
		return ToolInstallResult(tool_id=tool_id, ok=True)

	def _install_zip_flatten(self, tool_id: str, entry: dict[str, Any]) -> ToolInstallResult:
		url = str(entry.get("url", ""))
		prefix = str(entry.get("prefix", ""))
		if not url:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Missing download URL")
		data = self._download_bytes(url)
		if not self._checksum_ok(data, entry):
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Checksum mismatch")
		members = self._archive_members(data, "zip")
		written = 0
		for name, payload in members.items():
			if prefix and not name.startswith(prefix):
				continue
			relative = name[len(prefix) :] if prefix and name.startswith(prefix) else name
			if not relative or relative.endswith("/"):
				continue
			dest = self._dest.joinpath(*relative.split("/"))
			dest.parent.mkdir(parents=True, exist_ok=True)
			dest.write_bytes(payload)
			if not self._windows:
				self._make_executable(dest)
			written += 1
		if written == 0:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Archive extracted nothing")
		launcher = entry.get("launcher")
		if launcher:
			launcher_path = self._dest / str(launcher)
			primary = bundled_tool_path(
				BundledTool(tool_id),
				root=self._dest,
				platform_is_windows=self._windows,
			)
			if launcher_path.is_file() and not primary.is_file():
				shutil.copy2(launcher_path, primary)
		primary = bundled_tool_path(
			BundledTool(tool_id),
			root=self._dest,
			platform_is_windows=self._windows,
		)
		if not primary.is_file():
			return ToolInstallResult(
				tool_id=tool_id,
				ok=False,
				message=f"Expected {primary.name} after extract",
			)
		return ToolInstallResult(tool_id=tool_id, ok=True)

	def _install_archive(self, tool_id: str, entry: dict[str, Any], *, kind: str) -> ToolInstallResult:
		url = str(entry.get("url", ""))
		files = entry.get("files", {})
		if not url or not isinstance(files, dict) or not files:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Invalid archive catalog entry")
		data = self._download_bytes(url)
		if not self._checksum_ok(data, entry):
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Checksum mismatch")
		members = self._archive_members(data, kind)
		written = 0
		for name, inner in files.items():
			payload = self._read_archive_member(members, str(inner))
			if payload is None:
				return ToolInstallResult(tool_id=tool_id, ok=False, message=f"Archive missing {inner}")
			dest = bundled_tool_path(BundledTool(str(name)), root=self._dest, platform_is_windows=self._windows)
			dest.write_bytes(payload)
			self._make_executable(dest)
			written += 1
		if written == 0:
			return ToolInstallResult(tool_id=tool_id, ok=False, message="Archive extracted nothing")
		return ToolInstallResult(tool_id=tool_id, ok=True)

	def _archive_members(self, data: bytes, kind: str) -> dict[str, bytes]:
		out: dict[str, bytes] = {}
		if kind == "zip":
			with zipfile.ZipFile(io.BytesIO(data)) as archive:
				for name in archive.namelist():
					if name.endswith("/"):
						continue
					out[name] = archive.read(name)
			return out
		with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
			for member in archive.getmembers():
				if not member.isfile():
					continue
				extracted = archive.extractfile(member)
				if extracted is None:
					continue
				out[member.name] = extracted.read()
		return out

	def _read_archive_member(self, members: dict[str, bytes], inner: str) -> bytes | None:
		if inner in members:
			return members[inner]
		suffix = inner.lstrip("*/")
		matches = [name for name in members if name == inner or name.endswith("/" + suffix) or name.endswith(suffix)]
		if len(matches) == 1:
			return members[matches[0]]
		basename = suffix.rsplit("/", 1)[-1]
		base_matches = [name for name in members if name.rsplit("/", 1)[-1] == basename]
		if len(base_matches) == 1:
			return members[base_matches[0]]
		return None

	def _install_static_ffmpeg_wheel(self, entry: dict[str, Any]) -> ToolInstallResult:
		version = str(entry.get("version", ""))
		if not version:
			return ToolInstallResult(tool_id="ffmpeg", ok=False, message="Missing wheel version")
		meta_url = f"https://pypi.org/pypi/static-ffmpeg/{version}/json"
		response = httpx.get(meta_url, timeout=120.0, follow_redirects=True)
		response.raise_for_status()
		meta = response.json()
		wheel_url = self._pick_wheel_url(meta)
		if not wheel_url:
			return ToolInstallResult(tool_id="ffmpeg", ok=False, message="No compatible static-ffmpeg wheel")
		data = self._download_bytes(wheel_url)
		with zipfile.ZipFile(io.BytesIO(data)) as archive:
			ffmpeg_member = self._find_wheel_member(archive, "ffmpeg")
			ffprobe_member = self._find_wheel_member(archive, "ffprobe")
			if not ffmpeg_member or not ffprobe_member:
				return ToolInstallResult(tool_id="ffmpeg", ok=False, message="Wheel missing ffmpeg/ffprobe")
			ffmpeg_bytes = archive.read(ffmpeg_member)
			ffprobe_bytes = archive.read(ffprobe_member)
		ffmpeg_dest = bundled_tool_path(BundledTool.FFMPEG, root=self._dest, platform_is_windows=self._windows)
		ffprobe_dest = bundled_tool_path(BundledTool.FFPROBE, root=self._dest, platform_is_windows=self._windows)
		ffmpeg_dest.write_bytes(ffmpeg_bytes)
		ffprobe_dest.write_bytes(ffprobe_bytes)
		self._make_executable(ffmpeg_dest)
		self._make_executable(ffprobe_dest)
		return ToolInstallResult(tool_id="ffmpeg", ok=True)

	def _pick_wheel_url(self, meta: dict[str, Any]) -> str | None:
		urls = meta.get("urls", [])
		for item in urls:
			if isinstance(item, dict) and item.get("packagetype") == "bdist_wheel":
				return str(item.get("url", ""))
		return None

	def _find_wheel_member(self, archive: zipfile.ZipFile, name: str) -> str | None:
		for member in archive.namelist():
			base = member.rsplit("/", 1)[-1]
			if base == name or base == f"{name}.exe":
				return member
		return None

	def _download_bytes(self, url: str) -> bytes:
		try:
			response = httpx.get(url, timeout=300.0, follow_redirects=True)
			response.raise_for_status()
		except httpx.HTTPStatusError as exc:
			status = exc.response.status_code
			if status == 404:
				raise RuntimeError(f"Download not found (HTTP 404): {url}") from exc
			raise RuntimeError(f"Download failed (HTTP {status}): {url}") from exc
		return response.content

	def _checksum_ok(self, data: bytes, entry: dict[str, Any]) -> bool:
		expected = entry.get("sha256")
		if not expected:
			return True
		return hashlib.sha256(data).hexdigest() == str(expected)

	def _make_executable(self, path: Path) -> None:
		if sys.platform == "win32":
			return
		mode = path.stat().st_mode
		path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
