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
