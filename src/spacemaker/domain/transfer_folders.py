from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path


class TransferFolder(StrEnum):
	"""Device folder labels for USB file transfer (any file types)."""

	DOWNLOAD = "download"
	DOCUMENTS = "documents"
	DCIM = "dcim"
	PICTURES = "pictures"
	MOVIES = "movies"
	MUSIC = "music"


ALL_TRANSFER_FOLDERS: frozenset[TransferFolder] = frozenset(TransferFolder)

DEFAULT_ANDROID_TRANSFER_FOLDERS: frozenset[TransferFolder] = frozenset(
	{TransferFolder.DOWNLOAD, TransferFolder.DOCUMENTS},
)

DEFAULT_IPHONE_TRANSFER_FOLDERS: frozenset[TransferFolder] = frozenset({TransferFolder.DCIM})

_FOLDER_PATH_MARKERS: dict[TransferFolder, frozenset[str]] = {
	TransferFolder.DOWNLOAD: frozenset({"download", "downloads"}),
	TransferFolder.DOCUMENTS: frozenset({"documents", "docs"}),
	TransferFolder.DCIM: frozenset({"dcim"}),
	TransferFolder.PICTURES: frozenset({"pictures"}),
	TransferFolder.MOVIES: frozenset({"movies"}),
	TransferFolder.MUSIC: frozenset({"music"}),
}

# Longest Android user-storage roots first (path segments, lowercased).
_ANDROID_USER_STORAGE_PREFIX_PARTS: tuple[tuple[str, ...], ...] = (
	("storage", "self", "primary"),
	("storage", "emulated", "0"),
	("sdcard",),
)


def strip_android_user_storage_prefix(path: str) -> str:
	"""Drop known Android user-storage roots; keep remaining relative segments.

	``/storage/emulated/0/Download/a.pdf`` → ``Download/a.pdf``;
	``sdcard/WhatsApp/Media`` → ``WhatsApp/Media``.
	Empty string if the path is only a storage root (or empty input).
	"""
	text = (path or "").strip().replace("\\", "/")
	parts = [p for p in text.split("/") if p]
	if not parts:
		return ""
	lower = [p.lower() for p in parts]
	for prefix in _ANDROID_USER_STORAGE_PREFIX_PARTS:
		n = len(prefix)
		if lower[:n] == list(prefix):
			return "/".join(parts[n:])
	return "/".join(parts)


def parse_transfer_folders(values: list[str]) -> frozenset[TransferFolder]:
	out: set[TransferFolder] = set()
	for raw in values:
		try:
			out.add(TransferFolder(raw.lower()))
		except ValueError:
			continue
	return frozenset(out)


def path_matches_transfer_folders(device_path: str, selected: frozenset[TransferFolder]) -> bool:
	if not selected:
		return False
	normalized = device_path.lstrip("/").lower().replace("\\", "/")
	parts = frozenset(normalized.split("/"))
	for folder in selected:
		markers = _FOLDER_PATH_MARKERS[folder]
		if parts & markers:
			return True
	return False


def normalize_device_relative_path(path: str) -> str | None:
	"""Normalize a device-relative path; reject empty or ``..`` segments.

	Strips Android user-storage prefixes so extras stay flat
	(``storage/self/primary/WhatsApp`` → ``WhatsApp``).
	"""
	text = (path or "").strip().replace("\\", "/").lstrip("/")
	if not text:
		return None
	flattened = strip_android_user_storage_prefix(text)
	if not flattened:
		return None
	parts = [p for p in flattened.split("/") if p and p != "."]
	if not parts or any(p == ".." for p in parts):
		return None
	return "/".join(parts)


def host_path_to_device_relative(mount_root: str, host_path: str) -> str | None:
	"""Map a host path under the phone mount to a device-relative path."""
	try:
		mount = Path(mount_root).resolve()
		target = Path(host_path).resolve()
	except OSError:
		return None
	try:
		relative = target.relative_to(mount)
	except ValueError:
		return None
	return normalize_device_relative_path(relative.as_posix())


def existing_transfer_folders_from_dir_names(dir_names: Iterable[str]) -> frozenset[TransferFolder]:
	"""Preset folders whose path markers appear in directory names under the mount."""
	names = {name.strip().lower() for name in dir_names if name and name.strip()}
	if not names:
		return frozenset()
	found: set[TransferFolder] = set()
	for folder, markers in _FOLDER_PATH_MARKERS.items():
		if names & markers:
			found.add(folder)
	return frozenset(found)


def path_matches_extra_sources(device_path: str, extras: frozenset[str]) -> bool:
	"""True if device_path is an extra file or lies under an extra folder.

	Extras are mount-relative (e.g. ``WhatsApp/Media``) while device paths from
	ADB are often absolute (``/sdcard/WhatsApp/Media/a.jpg``). Match when the
	extra path appears as consecutive path components.
	"""
	if not extras:
		return False
	device_parts = [p for p in device_path.replace("\\", "/").split("/") if p]
	if not device_parts:
		return False
	device_lower = [p.lower() for p in device_parts]
	for raw in extras:
		extra = normalize_device_relative_path(raw.lstrip("/"))
		if extra is None:
			continue
		extra_parts = extra.lower().split("/")
		n, m = len(device_lower), len(extra_parts)
		if m > n:
			continue
		for i in range(n - m + 1):
			if device_lower[i : i + m] == extra_parts:
				return True
	return False


def merge_extra_paths(existing: Iterable[str], additions: Iterable[str]) -> list[str]:
	"""Append normalized extras; skip duplicates (case-insensitive)."""
	out: list[str] = []
	seen: set[str] = set()
	for raw in list(existing) + list(additions):
		normalized = normalize_device_relative_path(raw.lstrip("/"))
		if normalized is None:
			continue
		key = normalized.lower()
		if key in seen:
			continue
		seen.add(key)
		out.append(normalized)
	return out
