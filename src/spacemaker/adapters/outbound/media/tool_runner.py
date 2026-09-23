from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from spacemaker.adapters.outbound.media.ffmpeg_encoders import hardware_video_encoder_from_ffmpeg_encoders
from spacemaker.bootstrap.bundled_tools import (
	BundledTool,
	bundle_root,
	bundled_tool_path,
	is_frozen,
	resolve_tool_path,
)
from spacemaker.domain.video_encode import HardwareVideoEncoder


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
		path_fallback_allowed: Callable[[BundledTool], bool] | None = None,
	) -> None:
		self._root = bundle_root_path or bundle_root()
		if platform_is_windows is None:
			import sys

			platform_is_windows = sys.platform == "win32"
		self._windows = platform_is_windows
		self._path_fallback_allowed = path_fallback_allowed or (lambda _tool: True)
		self._ffmpeg_path: Path | None = None
		self._magick_path: Path | None = None

	def path(self, tool: BundledTool) -> Path:
		if tool is BundledTool.FFMPEG:
			return self._resolve_ffmpeg_path()
		if tool is BundledTool.MAGICK:
			return self._resolve_magick_path()
		return resolve_tool_path(
			tool,
			frozen=is_frozen(),
			dev_mode=False,
			bundle_root_path=self._root,
			platform_is_windows=self._windows,
			allow_path_fallback=self._path_fallback_allowed(tool),
		)

	def _resolve_ffmpeg_path(self) -> Path:
		if self._ffmpeg_path is not None:
			return self._ffmpeg_path
		allow_path = self._path_fallback_allowed(BundledTool.FFMPEG)
		managed = bundled_tool_path(BundledTool.FFMPEG, root=self._root, platform_is_windows=self._windows)
		chosen = resolve_tool_path(
			BundledTool.FFMPEG,
			frozen=is_frozen(),
			dev_mode=False,
			bundle_root_path=self._root,
			platform_is_windows=self._windows,
			allow_path_fallback=allow_path,
		)
		if allow_path and managed.is_file():
			vaapi = Path("/dev/dri/renderD128").exists()
			managed_text = self._ffmpeg_encoders_text_at(managed)
			if hardware_video_encoder_from_ffmpeg_encoders(managed_text, vaapi_render_node=vaapi) is HardwareVideoEncoder.NONE:
				search = "ffmpeg.exe" if self._windows else "ffmpeg"
				system = shutil.which(search)
				if system:
					system_path = Path(system).resolve()
					if system_path != managed.resolve():
						system_text = self._ffmpeg_encoders_text_at(system_path)
						if (
							hardware_video_encoder_from_ffmpeg_encoders(
								system_text,
								vaapi_render_node=vaapi,
							)
							is not HardwareVideoEncoder.NONE
						):
							self._ffmpeg_path = system_path
							return self._ffmpeg_path
		self._ffmpeg_path = chosen
		return self._ffmpeg_path

	def _resolve_magick_path(self) -> Path:
		if self._magick_path is not None:
			return self._magick_path
		allow_path = self._path_fallback_allowed(BundledTool.MAGICK)
		managed = bundled_tool_path(BundledTool.MAGICK, root=self._root, platform_is_windows=self._windows)
		chosen = resolve_tool_path(
			BundledTool.MAGICK,
			frozen=is_frozen(),
			dev_mode=False,
			bundle_root_path=self._root,
			platform_is_windows=self._windows,
			allow_path_fallback=allow_path,
		)
		if managed.is_file() and not self._tool_version_ok(managed):
			for name in ("magick", "convert"):
				system = shutil.which(name)
				if system:
					system_path = Path(system).resolve()
					if self._tool_version_ok(system_path):
						self._magick_path = system_path
						return self._magick_path
		self._magick_path = chosen
		return self._magick_path

	def _tool_version_ok(self, tool_path: Path) -> bool:
		result = subprocess.run(  # noqa: S603
			[str(tool_path), "-version"],
			capture_output=True,
			text=True,
			check=False,
		)
		return result.returncode == 0

	def _ffmpeg_encoders_text_at(self, ffmpeg_path: Path) -> str:
		result = subprocess.run(  # noqa: S603
			[str(ffmpeg_path), "-encoders"],
			capture_output=True,
			text=True,
			check=False,
		)
		return result.stdout + result.stderr

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
