from __future__ import annotations

import shutil
import threading
from pathlib import Path

from spacemaker.bootstrap.bundled_tools import (
	BundledTool,
	bundled_tool_path,
	is_dev_mode,
	managed_tool_present,
	resolve_tool_source,
	tools_install_root,
)
from spacemaker.bootstrap.paths import (
	clear_components_setup_complete,
	load_components_setup_complete,
	managed_tools_dir,
	save_components_setup_complete,
)
from spacemaker.bootstrap.platform_setup_hints import components_setup_hint
from spacemaker.domain.managed_tool import ManagedToolStatus, ToolInstallPhase, ToolResolution
from spacemaker.ports.outbound.tool_installer import ToolInstallerPort


class ManagedToolsService:
	def __init__(self, installer: ToolInstallerPort, *, dest_dir: Path | None = None) -> None:
		self._installer = installer
		self._dest = dest_dir or managed_tools_dir()
		self._lock = threading.Lock()
		self._phase: dict[str, ToolInstallPhase] = {}
		self._messages: dict[str, str] = {}
		self._path_fallback_allowed = False
		self._setup_complete = False
		if load_components_setup_complete(tools_dir=self._dest):
			self._path_fallback_allowed = True
			self._setup_complete = True

	def tools_dir(self) -> Path:
		return self._dest

	def delete_downloaded(self) -> None:
		root = self._dest.resolve()
		if root.is_dir():
			shutil.rmtree(root)
		root.mkdir(parents=True, exist_ok=True)
		with self._lock:
			self._phase.clear()
			self._messages.clear()
			self._path_fallback_allowed = False
			self._setup_complete = False
		clear_components_setup_complete(tools_dir=self._dest)

	def allow_path_fallback(self) -> None:
		with self._lock:
			self._path_fallback_allowed = True
			self._setup_complete = True
		save_components_setup_complete(tools_dir=self._dest)

	def permit_path_fallback(self, tool: BundledTool) -> bool:
		if is_dev_mode():
			return True
		import sys

		windows = sys.platform == "win32"
		root = tools_install_root()
		if managed_tool_present(tool, bundle_root_path=root, platform_is_windows=windows):
			return True
		with self._lock:
			return self._path_fallback_allowed

	def ensure_all(self) -> list[ManagedToolStatus]:
		for tool in BundledTool:
			self._ensure_one(tool)
		return self.snapshot()

	def _ensure_one(self, tool: BundledTool) -> None:
		import sys

		windows = sys.platform == "win32"
		managed = bundled_tool_path(tool, root=tools_install_root(), platform_is_windows=windows)
		if managed.is_file():
			return
		tool_id = tool.value
		if not self._installer.has_catalog_entry(tool_id):
			with self._lock:
				if not self._installer.catalog_covers(tool_id):
					self._messages[tool_id] = "No portable download for this OS — install it, then Continue to use PATH"
			return
		with self._lock:
			self._phase[tool_id] = ToolInstallPhase.DOWNLOADING
		result = self._installer.install(tool_id)
		with self._lock:
			if result.ok:
				self._phase[tool_id] = ToolInstallPhase.READY
				self._messages.pop(tool_id, None)
			else:
				self._phase[tool_id] = ToolInstallPhase.FAILED
				self._messages[tool_id] = result.message or "Download failed"

	def snapshot(self) -> list[ManagedToolStatus]:
		import sys

		windows = sys.platform == "win32"
		out: list[ManagedToolStatus] = []
		for tool in BundledTool:
			tool_id = tool.value
			with self._lock:
				phase = self._phase.get(tool_id, ToolInstallPhase.IDLE)
				message = self._messages.get(tool_id)
			if phase == ToolInstallPhase.DOWNLOADING:
				out.append(
					ManagedToolStatus(
						tool_id=tool_id,
						phase=ToolInstallPhase.DOWNLOADING,
						resolution=ToolResolution.MISSING,
						path=None,
						message=message,
					),
				)
				continue
			allow_path = self.permit_path_fallback(tool)
			if not allow_path and self._installer.has_catalog_entry(tool_id) and phase == ToolInstallPhase.IDLE:
				out.append(
					ManagedToolStatus(
						tool_id=tool_id,
						phase=ToolInstallPhase.DOWNLOADING,
						resolution=ToolResolution.MISSING,
						path=None,
						message="Waiting for download",
					),
				)
				continue
			try:
				path, source = resolve_tool_source(
					tool,
					bundle_root_path=tools_install_root(),
					platform_is_windows=windows,
					allow_path_fallback=allow_path,
				)
				resolution = ToolResolution.MANAGED if source == "managed" else ToolResolution.PATH
				out.append(
					ManagedToolStatus(
						tool_id=tool_id,
						phase=ToolInstallPhase.READY if phase != ToolInstallPhase.DOWNLOADING else phase,
						resolution=resolution,
						path=str(path),
						message=message,
					),
				)
			except FileNotFoundError:
				if not self._installer.catalog_covers(tool_id):
					fail_msg = message or "No portable download for this OS — install it, then Continue to use PATH"
				else:
					fail_msg = message or "Download missing — Retry, or Continue to use a system install"
				out.append(
					ManagedToolStatus(
						tool_id=tool_id,
						phase=phase if phase != ToolInstallPhase.IDLE else ToolInstallPhase.FAILED,
						resolution=ToolResolution.MISSING,
						path=None,
						message=fail_msg,
					),
				)
		return out

	def all_resolved(self) -> bool:
		return all(item.resolution != ToolResolution.MISSING for item in self.snapshot())

	def downloads_pending(self) -> bool:
		"""True when a catalog tool is not yet present in the managed folder (PATH ignored)."""
		import sys

		windows = sys.platform == "win32"
		root = tools_install_root()
		for tool in BundledTool:
			if not self._installer.catalog_covers(tool.value):
				continue
			if not managed_tool_present(tool, bundle_root_path=root, platform_is_windows=windows):
				return True
		return False

	def setup_pending(self) -> bool:
		with self._lock:
			if self._setup_complete:
				return False
		if self.downloads_pending():
			return True
		return not self.all_resolved()

	def status_dict(self) -> dict[str, object]:
		items = self.snapshot()
		tool_rows = [
			{
				"tool_id": item.tool_id,
				"phase": item.phase.value,
				"resolution": item.resolution.value,
				"path": item.path,
				"message": item.message,
			}
			for item in items
		]
		hint = components_setup_hint(tools=tool_rows)
		payload: dict[str, object] = {
			"tools_dir": str(self._dest),
			"all_ready": self.all_resolved(),
			"downloads_pending": self.downloads_pending(),
			"setup_pending": self.setup_pending(),
			"tools": tool_rows,
		}
		if hint:
			payload["setup_hint"] = hint
		return payload
