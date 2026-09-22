from __future__ import annotations

import subprocess
from pathlib import Path

from spacemaker.bootstrap.bundled_tools import BundledTool, bundle_root, is_dev_mode, is_frozen, resolve_tool_path


class ToolExecutionError(RuntimeError):
	def __init__(self, tool: BundledTool, command: list[str], result: subprocess.CompletedProcess[str]) -> None:
		self.tool = tool
		self.command = command
		self.result = result
		detail = (result.stderr or result.stdout or "").strip()
		if len(detail) > 800:
			detail = detail[:800] + "…"
		message = f"{tool.value} failed (exit {result.returncode})"
		if detail:
			message = f"{message}: {detail}"
		super().__init__(message)


class ToolRunner:
	def __init__(
		self,
		*,
		bundle_root_path: Path | None = None,
		platform_is_windows: bool | None = None,
	) -> None:
		self._root = bundle_root_path or bundle_root()
		if platform_is_windows is None:
			import sys

			platform_is_windows = sys.platform == "win32"
		self._windows = platform_is_windows

	def path(self, tool: BundledTool) -> Path:
		return resolve_tool_path(
			tool,
			frozen=is_frozen(),
			dev_mode=is_dev_mode(),
			bundle_root_path=self._root,
			platform_is_windows=self._windows,
		)

	def run(  # noqa: S603
		self,
		tool: BundledTool,
		args: list[str],
		*,
		check: bool = True,
	) -> subprocess.CompletedProcess[str]:
		cmd = [str(self.path(tool)), *args]
		result = subprocess.run(cmd, capture_output=True, text=True, check=False)
		if check and result.returncode != 0:
			raise ToolExecutionError(tool, cmd, result)
		return result
