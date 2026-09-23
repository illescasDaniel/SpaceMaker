from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from spacemaker.bootstrap.paths import managed_tools_dir


class BundledTool(StrEnum):
	ADB = "adb"
	FFMPEG = "ffmpeg"
	FFPROBE = "ffprobe"
	MAGICK = "magick"
	EXIFTOOL = "exiftool"
	MTP_DETECT = "mtp-detect"
	MTP_GETFILE = "mtp-getfile"
	IDEVICE_ID = "idevice_id"
	IDEVICE_PAIR = "idevicepair"
	IDEVICE_INFO = "ideviceinfo"
	IFUSE = "ifuse"


def is_frozen() -> bool:
	return bool(getattr(sys, "frozen", False))


def is_dev_mode() -> bool:
	return os.environ.get("SPACEMAKER_DEV", "").lower() in {"1", "true", "yes"}


def tools_install_root() -> Path:
	override = os.environ.get("SPACEMAKER_TOOLS_DIR", "").strip()
	if override:
		return Path(override).expanduser().resolve()
	return managed_tools_dir()


def bundle_root(exe_dir: Path | None = None) -> Path:
	if exe_dir is not None:
		return exe_dir
	return tools_install_root()


def bundled_tool_path(tool: BundledTool, *, root: Path, platform_is_windows: bool) -> Path:
	name = tool.value
	if platform_is_windows:
		name = f"{name}.exe"
	return root / name


def _executable_file(path: Path) -> bool:
	return path.is_file()


def managed_tool_present(
	tool: BundledTool,
	*,
	bundle_root_path: Path | None = None,
	platform_is_windows: bool | None = None,
) -> bool:
	if platform_is_windows is None:
		platform_is_windows = sys.platform == "win32"
	root = bundle_root_path or tools_install_root()
	candidate = bundled_tool_path(tool, root=root, platform_is_windows=platform_is_windows)
	return _executable_file(candidate)


def resolve_tool_path(
	tool: BundledTool,
	*,
	frozen: bool = False,
	dev_mode: bool = False,
	bundle_root_path: Path | None = None,
	platform_is_windows: bool | None = None,
	which: Callable[[str], str | None] | None = None,
	allow_path_fallback: bool = True,
) -> Path:
	_ = frozen
	_ = dev_mode
	lookup = which if which is not None else shutil.which
	if platform_is_windows is None:
		platform_is_windows = sys.platform == "win32"
	root = bundle_root_path or tools_install_root()
	candidate = bundled_tool_path(tool, root=root, platform_is_windows=platform_is_windows)
	if _executable_file(candidate):
		return candidate
	if allow_path_fallback:
		search = f"{tool.value}.exe" if platform_is_windows else tool.value
		found = lookup(search)
		if found:
			return Path(found)
	raise FileNotFoundError(
		f"Tool not found: {tool.value} (not in {root} and not on PATH). Use Components setup or install manually.",
	)


def resolve_tool_source(
	tool: BundledTool,
	*,
	bundle_root_path: Path | None = None,
	platform_is_windows: bool | None = None,
	which: Callable[[str], str | None] | None = None,
	allow_path_fallback: bool = True,
) -> tuple[Path, str]:
	"""Return (path, source) where source is 'managed' or 'path'."""
	if platform_is_windows is None:
		platform_is_windows = sys.platform == "win32"
	root = bundle_root_path or tools_install_root()
	candidate = bundled_tool_path(tool, root=root, platform_is_windows=platform_is_windows)
	if _executable_file(candidate):
		return candidate, "managed"
	path = resolve_tool_path(
		tool,
		bundle_root_path=root,
		platform_is_windows=platform_is_windows,
		which=which,
		allow_path_fallback=allow_path_fallback,
	)
	return path, "path"


def missing_bundled_tools(
	*,
	bundle_root_path: Path | None = None,
	platform_is_windows: bool | None = None,
) -> list[str]:
	missing: list[str] = []
	for tool in BundledTool:
		try:
			resolve_tool_path(
				tool,
				bundle_root_path=bundle_root_path,
				platform_is_windows=platform_is_windows,
				allow_path_fallback=True,
			)
		except FileNotFoundError:
			missing.append(tool.value)
	return missing


def bundled_tools_hint() -> str:
	return (
		"Open Components setup or Settings in the app, retry downloads, "
		"or set SPACEMAKER_TOOLS_DIR to a folder containing the tools."
	)
