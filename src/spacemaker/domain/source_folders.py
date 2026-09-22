from __future__ import annotations

from enum import StrEnum


class SourceFolder(StrEnum):
	DCIM = "dcim"
	PICTURES = "pictures"
	MOVIES = "movies"


ALL_SOURCE_FOLDERS: frozenset[SourceFolder] = frozenset(SourceFolder)


def parse_source_folders(values: list[str]) -> frozenset[SourceFolder]:
	out: set[SourceFolder] = set()
	for raw in values:
		try:
			out.add(SourceFolder(raw.lower()))
		except ValueError:
			continue
	return frozenset(out) if out else ALL_SOURCE_FOLDERS


def path_matches_source_folders(device_path: str, selected: frozenset[SourceFolder]) -> bool:
	normalized = device_path.lstrip("/").lower().replace("\\", "/")
	parts = normalized.split("/")
	for folder in selected:
		if folder is SourceFolder.DCIM and any(part == "dcim" for part in parts):
			return True
		if folder is SourceFolder.PICTURES and any(part == "pictures" for part in parts):
			return True
		if folder is SourceFolder.MOVIES and any(part == "movies" for part in parts):
			return True
	return False
