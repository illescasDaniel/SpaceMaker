from __future__ import annotations

import os
import sys
from pathlib import Path

from spacemaker.domain.library import LIBRARY_FOLDERS


def documents_directory() -> Path:
	home = Path.home()
	candidates: list[Path] = [home / "Documents"]
	if sys.platform == "linux":
		xdg = os.environ.get("XDG_DOCUMENTS_DIR")
		if xdg:
			candidates.insert(0, Path(xdg))
	if sys.platform == "darwin":
		candidates = [home / "Documents"]
	for candidate in candidates:
		if candidate.is_dir():
			return candidate
	return candidates[0]


def default_documents_receive_root() -> str:
	return str((documents_directory() / "SpaceMaker").resolve())


def documents_folder_open_target() -> Path:
	"""Receive destination if it exists; otherwise the user's Documents directory."""
	spacemaker = Path(default_documents_receive_root())
	if spacemaker.is_dir():
		return spacemaker
	return documents_directory()


def pictures_directory() -> Path:
	home = Path.home()
	candidates: list[Path] = [home / "Pictures"]
	if sys.platform == "linux":
		xdg = os.environ.get("XDG_PICTURES_DIR")
		if xdg:
			candidates.insert(0, Path(xdg))
	if sys.platform == "darwin":
		candidates = [home / "Pictures", home / "Photos"]
	for candidate in candidates:
		if candidate.is_dir():
			return candidate
	return candidates[0]


def default_library_root() -> str:
	return str((pictures_directory() / "SpaceMakerLibrary").resolve())


def display_user_path(path: str, *, trailing_slash: bool = False) -> str:
	text = path.strip()
	if not text:
		return ""
	home = str(Path.home())
	resolved = str(Path(text).expanduser().resolve())
	if resolved == home:
		display = "~"
	elif resolved.startswith(home + os.sep):
		display = "~" + resolved[len(home) :].replace(os.sep, "/")
	else:
		display = resolved
	if trailing_slash and not display.endswith("/"):
		display += "/"
	return display


def webengine_storage_path() -> str:
	from spacemaker.bootstrap.ui_shell import webengine_profile_slug

	base = Path.home() / ".cache" / "spacemaker" / "webengine" / webengine_profile_slug()
	base.mkdir(parents=True, exist_ok=True)
	return str(base)


def bundle_resource_root() -> Path | None:
	"""Linux AppImage / AppDir share tree (legal, tool catalog, icon)."""
	override = os.environ.get("SPACEMAKER_BUNDLE_ROOT", "").strip()
	if override:
		root = Path(override)
		if root.is_dir():
			return root
	appdir = os.environ.get("APPDIR", "").strip()
	if appdir:
		share = Path(appdir) / "usr" / "share" / "spacemaker"
		if share.is_dir():
			return share
	if getattr(sys, "frozen", False):
		meipass = getattr(sys, "_MEIPASS", None)
		if meipass:
			return Path(meipass)
	return None


def app_icon_path() -> Path | None:
	"""PNG used for the desktop window / task switcher (dev tree + PyInstaller bundle)."""
	candidates: list[Path] = []
	bundled = bundle_resource_root()
	if bundled is not None:
		candidates.append(bundled / "packaging" / "assets" / "spacemaker-icon.png")
	if getattr(sys, "frozen", False):
		meipass = getattr(sys, "_MEIPASS", None)
		if meipass:
			candidates.append(Path(meipass) / "packaging" / "assets" / "spacemaker-icon.png")
	dev_root = Path(__file__).resolve().parents[3]
	candidates.append(dev_root / "packaging" / "assets" / "spacemaker-icon.png")
	for path in candidates:
		if path.is_file():
			return path
	return None


def managed_tools_dir() -> Path:
	if sys.platform == "win32":
		local = os.environ.get("LOCALAPPDATA", "")
		base = Path(local) / "SpaceMaker" if local else Path.home() / "AppData" / "Local" / "SpaceMaker"
	elif sys.platform == "darwin":
		base = Path.home() / "Library" / "Application Support" / "SpaceMaker"
	else:
		xdg = os.environ.get("XDG_DATA_HOME")
		base = Path(xdg) / "spacemaker" if xdg else Path.home() / ".local" / "share" / "spacemaker"
	return base / "tools"


def ensure_managed_tools_dir() -> Path:
	tools = managed_tools_dir()
	tools.mkdir(parents=True, exist_ok=True)
	return tools


def spacemaker_data_dir(*, tools_dir: Path | None = None) -> Path:
	return (tools_dir or managed_tools_dir()).parent


def user_preferences_path(*, tools_dir: Path | None = None) -> Path:
	"""Disk-backed preferences (e.g. Compress media) next to managed tools data."""
	return spacemaker_data_dir(tools_dir=tools_dir) / "preferences.json"


def components_setup_complete_marker(*, tools_dir: Path | None = None) -> Path:
	return spacemaker_data_dir(tools_dir=tools_dir) / "components_setup_complete"


def load_components_setup_complete(*, tools_dir: Path | None = None) -> bool:
	return components_setup_complete_marker(tools_dir=tools_dir).is_file()


def save_components_setup_complete(*, tools_dir: Path | None = None) -> None:
	path = components_setup_complete_marker(tools_dir=tools_dir)
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text("ok\n", encoding="utf-8")


def clear_components_setup_complete(*, tools_dir: Path | None = None) -> None:
	path = components_setup_complete_marker(tools_dir=tools_dir)
	if path.is_file():
		path.unlink()


def is_absolute_library_path(path: str) -> bool:
	text = path.strip()
	if not text:
		return False
	probe = Path(text)
	return probe.is_absolute()


def normalize_library_root(path: str) -> str:
	"""If the user picked a bucket folder (e.g. …/originals), use the library root parent."""
	text = path.strip()
	if not text:
		return ""
	probe = Path(text).expanduser()
	if not probe.is_absolute():
		return text
	resolved = probe.resolve()
	leaf_names = {folder.value for folder in LIBRARY_FOLDERS}
	if resolved.name.lower() in leaf_names:
		return str(resolved.parent)
	return str(resolved)
