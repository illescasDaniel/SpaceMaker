from __future__ import annotations

import shutil
import threading
from pathlib import Path

from spacemaker.bootstrap.bundled_tools import (
	BundledTool,
	bundled_tool_path,
	components_tools,
	ensure_host_tool_path_dirs,
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
from spacemaker.bootstrap.platform_setup_hints import (
	LinuxPackageFamily,
	ToolStatusHintRow,
	arch_install_prefix,
	detect_linux_package_family,
	install_all_command,
	install_command_for_tool,
	package_manager_command,
	show_iphone_usb_hint,
)
from spacemaker.domain.managed_tool import (
	ManagedToolStatus,
	ToolInstallPhase,
	ToolResolution,
	ToolsSummaryStatus,
	summarize_tool_resolutions,
	tools_summary_line,
)
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
		ensure_host_tool_path_dirs()
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
		for tool in components_tools():
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
		linux_family = None
		arch_prefix = None
		if sys.platform.startswith("linux"):
			linux_family = detect_linux_package_family()
			if linux_family == "arch":
				arch_prefix = arch_install_prefix()
		out: list[ManagedToolStatus] = []
		for tool in components_tools():
			tool_id = tool.value
			with self._lock:
				phase = self._phase.get(tool_id, ToolInstallPhase.IDLE)
				message = self._messages.get(tool_id)
			if phase == ToolInstallPhase.DOWNLOADING:
				out.append(
					self._status(
						tool_id=tool_id,
						phase=ToolInstallPhase.DOWNLOADING,
						resolution=ToolResolution.MISSING,
						path=None,
						message=message,
						linux_family=linux_family,
						arch_prefix=arch_prefix,
					),
				)
				continue
			# Live PATH probe for Components display (convert still gated by permit_path_fallback).
			if (
				not self.permit_path_fallback(tool)
				and self._installer.has_catalog_entry(tool_id)
				and phase == ToolInstallPhase.IDLE
			):
				out.append(
					self._status(
						tool_id=tool_id,
						phase=ToolInstallPhase.DOWNLOADING,
						resolution=ToolResolution.MISSING,
						path=None,
						message="Waiting for download",
						linux_family=linux_family,
						arch_prefix=arch_prefix,
					),
				)
				continue
			try:
				path, source = resolve_tool_source(
					tool,
					bundle_root_path=tools_install_root(),
					platform_is_windows=windows,
					allow_path_fallback=True,
				)
				resolution = ToolResolution.MANAGED if source == "managed" else ToolResolution.PATH
				out.append(
					self._status(
						tool_id=tool_id,
						phase=ToolInstallPhase.READY if phase != ToolInstallPhase.DOWNLOADING else phase,
						resolution=resolution,
						path=str(path),
						message=message,
						linux_family=linux_family,
						arch_prefix=arch_prefix,
					),
				)
			except FileNotFoundError:
				if not self._installer.catalog_covers(tool_id):
					fail_msg = message or "No portable download for this OS — install it, then Continue to use PATH"
				else:
					fail_msg = message or "Download missing — Retry, or Continue to use a system install"
				out.append(
					self._status(
						tool_id=tool_id,
						phase=phase if phase != ToolInstallPhase.IDLE else ToolInstallPhase.FAILED,
						resolution=ToolResolution.MISSING,
						path=None,
						message=fail_msg,
						linux_family=linux_family,
						arch_prefix=arch_prefix,
					),
				)
		return out

	def _status(
		self,
		*,
		tool_id: str,
		phase: ToolInstallPhase,
		resolution: ToolResolution,
		path: str | None,
		message: str | None,
		linux_family: LinuxPackageFamily | None = None,
		arch_prefix: str | None = None,
	) -> ManagedToolStatus:
		return ManagedToolStatus(
			tool_id=tool_id,
			phase=phase,
			resolution=resolution,
			path=path,
			message=message,
			install_command=install_command_for_tool(
				tool_id,
				phase=phase.value,
				resolution=resolution.value,
				linux_family=linux_family,
				arch_prefix=arch_prefix,
			),
		)

	def all_resolved(self) -> bool:
		return all(item.resolution != ToolResolution.MISSING for item in self.snapshot())

	def downloads_pending(self) -> bool:
		"""True when a catalog tool is not yet present in the managed folder (PATH ignored)."""
		import sys

		windows = sys.platform == "win32"
		root = tools_install_root()
		for tool in components_tools():
			if not self._installer.catalog_covers(tool.value):
				continue
			if not managed_tool_present(tool, bundle_root_path=root, platform_is_windows=windows):
				return True
		return False

	def setup_pending(self) -> bool:
		"""True until Continue when downloads pending, anything missing, or PATH-only tools need trust."""
		with self._lock:
			if self._setup_complete:
				return False
		if self.downloads_pending():
			return True
		items = self.snapshot()
		if any(item.resolution is ToolResolution.MISSING for item in items):
			return True
		# All resolve, but at least one is host PATH — Continue still needed to allow PATH fallback.
		if any(item.resolution is ToolResolution.PATH for item in items):
			return True
		return False

	def status_dict(self) -> dict[str, object]:
		import sys

		items = self.snapshot()
		resolutions = [item.resolution for item in items]
		summary = summarize_tool_resolutions(resolutions)
		managed_n = sum(1 for r in resolutions if r is ToolResolution.MANAGED)
		path_n = sum(1 for r in resolutions if r is ToolResolution.PATH)
		missing_n = sum(1 for r in resolutions if r is ToolResolution.MISSING)
		missing_ids = [item.tool_id for item in items if item.resolution is ToolResolution.MISSING]
		linux_family = None
		arch_prefix = None
		if sys.platform.startswith("linux"):
			linux_family = detect_linux_package_family()
			if linux_family == "arch":
				arch_prefix = arch_install_prefix()
		tool_rows: list[ToolStatusHintRow] = [
			{
				"tool_id": item.tool_id,
				"phase": item.phase.value,
				"resolution": item.resolution.value,
				"path": item.path,
				"message": item.message,
				"install_command": item.install_command,
			}
			for item in items
		]
		return {
			"tools_dir": str(self._dest),
			"all_ready": self.all_resolved(),
			"downloads_pending": self.downloads_pending(),
			"setup_pending": self.setup_pending(),
			"show_iphone_usb_hint": show_iphone_usb_hint(),
			"summary_status": summary.value,
			"summary_line": tools_summary_line(managed=managed_n, path=path_n, missing=missing_n),
			"details_expanded": summary is not ToolsSummaryStatus.OK,
			"package_manager_command": package_manager_command(linux_family=linux_family),
			"install_all_command": install_all_command(
				missing_ids,
				linux_family=linux_family,
				arch_prefix=arch_prefix,
			),
			"tools": tool_rows,
		}
