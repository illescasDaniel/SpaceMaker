from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path


class BundledTool(StrEnum):
	ADB = "adb"
	FFMPEG = "ffmpeg"
	FFPROBE = "ffprobe"
	MAGICK = "magick"
	EXIFTOOL = "exiftool"
	MTP_DETECT = "mtp-detect"
	MTP_GETFILE = "mtp-getfile"


def is_frozen() -> bool:
	return bool(getattr(sys, "frozen", False))


def is_dev_mode() -> bool:
	return os.environ.get("SPACEMAKER_DEV", "").lower() in {"1", "true", "yes"}


def bundle_root(exe_dir: Path | None = None) -> Path:
	if exe_dir is not None:
		return exe_dir / "tools"
	if is_frozen():
		return Path(sys.executable).resolve().parent / "tools"
	return Path(__file__).resolve().parents[3] / "tools"


def bundled_tool_path(tool: BundledTool, *, root: Path, platform_is_windows: bool) -> Path:
	name = tool.value
	if platform_is_windows:
		name = f"{name}.exe"
	return root / name


def missing_bundled_tools(
	*,
	bundle_root_path: Path | None = None,
	platform_is_windows: bool | None = None,
) -> list[str]:
	if platform_is_windows is None:
		platform_is_windows = sys.platform == "win32"
	root = bundle_root_path or bundle_root()
	missing: list[str] = []
	for tool in BundledTool:
		candidate = bundled_tool_path(tool, root=root, platform_is_windows=platform_is_windows)
		if not candidate.is_file():
			missing.append(tool.value)
	return missing


def bundled_tools_hint() -> str:
	return (
		"Copy release binaries into tools/ at the repo root, or run: "
		"uv run task dev-tools -- --from-path (dev only; uses PATH once to populate tools/)"
	)


def resolve_tool_path(
	tool: BundledTool,
	*,
	frozen: bool,
	dev_mode: bool,
	bundle_root_path: Path,
	platform_is_windows: bool,
	which: Callable[[str], str | None] = shutil.which,
) -> Path:
	candidate = bundled_tool_path(tool, root=bundle_root_path, platform_is_windows=platform_is_windows)
	if candidate.is_file():
		return candidate
	if frozen:
		raise FileNotFoundError(f"Bundled tool missing in release build: {tool.value} at {candidate}")
	if dev_mode:
		search = f"{tool.value}.exe" if platform_is_windows else tool.value
		found = which(search)
		if found:
			return Path(found)
		raise FileNotFoundError(
			f"Tool not found: {tool.value} (SPACEMAKER_DEV=1 and not on PATH). {bundled_tools_hint()}",
		)
	raise FileNotFoundError(f"Bundled tool missing: {tool.value} at {candidate}. {bundled_tools_hint()}")
