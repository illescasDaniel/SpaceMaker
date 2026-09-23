from __future__ import annotations

import os
import sys
from pathlib import Path

from spacemaker.domain.library import LIBRARY_FOLDERS


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


def webengine_storage_path() -> str:
	base = Path.home() / ".cache" / "spacemaker" / "webengine"
	base.mkdir(parents=True, exist_ok=True)
	return str(base)


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
