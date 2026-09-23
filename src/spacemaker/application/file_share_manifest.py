from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class EmptyShareSelectionError(ValueError):
	"""User selection resolves to zero shareable files."""


EMPTY_SHARE_FOLDER_MESSAGE = "This folder has no files. Choose a folder that contains at least one file."

ShareManifestKind = Literal["file", "folder_zip"]


@dataclass(frozen=True, slots=True)
class ShareDownloadTarget:
	kind: ShareManifestKind
	source_path: Path
	download_filename: str


@dataclass(frozen=True, slots=True)
class SharedManifestEntry:
	entry_id: str
	display_name: str
	kind: ShareManifestKind
	absolute_path: str


def count_shareable_files_in_root(path: Path) -> int:
	"""Count regular files under a share root (file itself or directory tree)."""
	resolved = path.expanduser().resolve()
	if not resolved.exists():
		return 0
	if resolved.is_file():
		return 1
	if resolved.is_dir():
		return sum(1 for child in resolved.rglob("*") if child.is_file())
	return 0


def dedupe_share_selection_paths(paths: list[str]) -> list[str]:
	"""Keep first occurrence of each top-level path (compared by resolved absolute path)."""
	seen: set[str] = set()
	out: list[str] = []
	for raw in paths:
		text = raw.strip()
		if not text:
			continue
		key = str(Path(text).expanduser().resolve())
		if key in seen:
			continue
		seen.add(key)
		out.append(text)
	return out


def prune_share_selection_paths(paths: list[str]) -> tuple[list[str], bool]:
	"""Drop folder paths with zero files. Returns (kept paths, had_empty_folder)."""
	kept: list[str] = []
	had_empty_folder = False
	for raw in paths:
		text = raw.strip()
		if not text:
			continue
		path = Path(text).expanduser().resolve()
		if path.is_dir():
			if count_shareable_files_in_root(path) == 0:
				had_empty_folder = True
				continue
		elif not path.is_file():
			continue
		kept.append(text)
	return kept, had_empty_folder


def build_share_manifest(paths: list[str]) -> list[SharedManifestEntry]:
	"""One manifest row per top-level selected path (file or folder zip)."""
	entries: list[SharedManifestEntry] = []
	index = 0
	for raw in paths:
		text = raw.strip()
		if not text:
			continue
		path = Path(text).expanduser().resolve()
		if not path.exists():
			continue
		if path.is_file():
			entries.append(
				SharedManifestEntry(
					entry_id=f"i{index}",
					display_name=path.name,
					kind="file",
					absolute_path=str(path),
				),
			)
			index += 1
			continue
		if path.is_dir() and count_shareable_files_in_root(path) > 0:
			entries.append(
				SharedManifestEntry(
					entry_id=f"i{index}",
					display_name=path.name,
					kind="folder_zip",
					absolute_path=str(path),
				),
			)
			index += 1
	return entries


def write_folder_zip(folder_root: Path, dest: Path) -> None:
	"""Write folder contents to dest, preserving relative paths inside the archive."""
	root = folder_root.expanduser().resolve()
	dest.parent.mkdir(parents=True, exist_ok=True)
	with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
		for child in sorted(root.rglob("*")):
			if not child.is_file():
				continue
			arcname = str(child.relative_to(root)).replace("\\", "/")
			archive.write(child, arcname)


def is_path_under_roots(candidate: Path, roots: list[Path]) -> bool:
	text = str(candidate.resolve())
	for root in roots:
		root_text = str(root.resolve())
		if text == root_text or text.startswith(root_text + "/") or text.startswith(root_text + "\\"):
			return True
	return False
