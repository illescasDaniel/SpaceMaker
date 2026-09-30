from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable, MutableMapping
from enum import StrEnum
from pathlib import Path

from spacemaker.bootstrap.paths import managed_tools_dir


class BundledTool(StrEnum):
	ADB = "adb"
	FFMPEG = "ffmpeg"
	FFPROBE = "ffprobe"
	MAGICK = "magick"
	AVIFENC = "avifenc"
	EXIFTOOL = "exiftool"
	IDEVICE_ID = "idevice_id"
	IDEVICE_PAIR = "idevicepair"
	IDEVICE_INFO = "ideviceinfo"
	IFUSE = "ifuse"


# iPhone USB / AFC — Linux-only on Components (extract-media / usb-file-transfer).
_AFC_COMPONENTS_TOOLS = frozenset(
	{
		BundledTool.IDEVICE_ID,
		BundledTool.IDEVICE_PAIR,
		BundledTool.IDEVICE_INFO,
		BundledTool.IFUSE,
	},
)


def components_tools(*, platform: str | None = None) -> tuple[BundledTool, ...]:
	"""Tools shown on Components for this OS (AFC tools are Linux-only)."""
	plat = platform if platform is not None else sys.platform
	if plat.startswith("linux"):
		return tuple(BundledTool)
	return tuple(tool for tool in BundledTool if tool not in _AFC_COMPONENTS_TOOLS)


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


def host_tool_path_dirs() -> list[Path]:
	"""Package-manager bin dirs that GUI / Dock launches often omit from PATH.

	macOS apps started outside a login shell typically lack Homebrew
	(``/opt/homebrew/bin`` on Apple Silicon, ``/usr/local/bin`` on Intel).
	Linux desktop entries often miss ``~/.local/bin``.
	"""
	candidates: list[Path] = []
	if sys.platform == "darwin":
		candidates.extend(
			(
				Path("/opt/homebrew/bin"),
				Path("/opt/homebrew/sbin"),
				Path("/usr/local/bin"),
				Path("/usr/local/sbin"),
			),
		)
	elif sys.platform.startswith("linux"):
		candidates.append(Path.home() / ".local" / "bin")
	return [path for path in candidates if path.is_dir()]


def ensure_host_tool_path_dirs(
	*,
	environ: MutableMapping[str, str] | None = None,
	extra_dirs: tuple[Path, ...] | None = None,
) -> list[str]:
	"""Prepend existing host tool dirs to ``PATH``; return dirs that were added."""
	env = os.environ if environ is None else environ
	current = env.get("PATH", "")
	parts = [part for part in current.split(os.pathsep) if part]
	seen = {str(Path(part)) for part in parts}
	dirs = list(extra_dirs) if extra_dirs is not None else host_tool_path_dirs()
	prepend: list[str] = []
	for directory in dirs:
		if not directory.is_dir():
			continue
		key = str(directory)
		if key in seen or key in prepend:
			continue
		prepend.append(key)
	if prepend:
		env["PATH"] = os.pathsep.join([*prepend, *parts]) if parts else os.pathsep.join(prepend)
	return prepend


def _tool_from_host_path_dirs(
	tool: BundledTool,
	*,
	platform_is_windows: bool,
	dirs: tuple[Path, ...] | None = None,
) -> Path | None:
	"""Fall back to well-known package-manager bins when ``which`` misses them."""
	name = f"{tool.value}.exe" if platform_is_windows else tool.value
	search = dirs if dirs is not None else tuple(host_tool_path_dirs())
	for directory in search:
		candidate = directory / name
		if _executable_file(candidate):
			return candidate
	return None


def _windows_magick_from_common_install_dirs(
	*,
	roots: tuple[Path, ...] | None = None,
) -> Path | None:
	"""ImageMagick winget/installer often lands under Program Files without updating PATH."""
	search_roots = roots
	if search_roots is None:
		search_roots = (Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)"))
	for base in search_roots:
		if not base.is_dir():
			continue
		for folder in sorted(base.glob("ImageMagick-*"), reverse=True):
			exe = folder / "magick.exe"
			if exe.is_file():
				return exe
	return None


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
		if tool is BundledTool.MAGICK and platform_is_windows:
			windows_magick = _windows_magick_from_common_install_dirs()
			if windows_magick is not None:
				return windows_magick
		host_hit = _tool_from_host_path_dirs(tool, platform_is_windows=platform_is_windows)
		if host_hit is not None:
			return host_hit
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
