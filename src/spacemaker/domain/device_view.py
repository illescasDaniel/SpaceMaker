"""Phone picker layout (List / Grid): folder-type table, media counts and the per-folder choice memory.

Resolution order (spec ``device-file-picker`` → **Grid view**): the user's stored choice for the folder,
then the folder type (``folder_view``), then auto-detection from ``DeviceFolderCounts``. Detection runs in
the web client from the page-1 counts; this module owns the facts it needs (the media extension set and the
folder-type table), so server and client never disagree.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from spacemaker.domain.device_browse import DeviceBrowseError, DeviceFolderCounts, folder_counts, normalize_browse_path
from spacemaker.domain.device_media import is_media_name


class DeviceViewMode(StrEnum):
	"""A concrete layout: a stored choice, a folder type, or what Auto resolved to."""

	LIST = "list"
	GRID = "grid"


class DeviceViewSetting(StrEnum):
	"""What the View control sends: ``AUTO`` forgets the folder's stored choice."""

	AUTO = "auto"
	LIST = "list"
	GRID = "grid"


DEVICE_VIEW_MEMORY_MAX = 500
"""Most folders remembered in ``device_picker_views``; the least recently set is dropped first."""

AUTO_GRID_MIN_MEDIA = 1
AUTO_GRID_MIN_RATIO = 0.6
"""Auto-detection: Grid when ``media_count >= AUTO_GRID_MIN_MEDIA`` and ``media_count >= ratio * entry_count``."""

GRID_FOLDER_NAMES: frozenset[str] = frozenset(
	name.casefold()
	for name in (
		"DCIM",
		"Pictures",
		"Movies",
		"Screenshots",
		"Camera",
		"WhatsApp Images",
		"WhatsApp Video",
		"Telegram Images",
		"Telegram Video",
	)
)
LIST_FOLDER_NAMES: frozenset[str] = frozenset(
	name.casefold() for name in ("Documents", "Download", "Android", "Music", "Podcasts", "Recordings")
)


@dataclass(frozen=True, slots=True)
class DeviceViewHints:
	"""What the client needs to resolve the layout of one folder (needs no listing).

	``folder_view`` comes from the folder-type table; ``stored_view`` is the user's choice for exactly this path.
	``None`` means "no opinion" (Auto at that level).
	"""

	folder_view: DeviceViewMode | None
	stored_view: DeviceViewMode | None


DeviceViewMemory = Mapping[str, DeviceViewMode]
"""Normalized device-relative path → stored choice, ordered least → most recently set."""

EMPTY_VIEW_MEMORY: DeviceViewMemory = MappingProxyType({})


def folder_view(path: str) -> DeviceViewMode | None:
	"""Folder-type layout of a normalized device-relative ``path``.

	Walks from the folder itself up to the root and returns the layout of the nearest whole segment whose
	case-insensitive name is in ``GRID_FOLDER_NAMES`` / ``LIST_FOLDER_NAMES``; ``None`` when none matches
	(including the root ``""``).
	"""
	for segment in reversed(path.split("/")):
		name = segment.casefold()
		if name in GRID_FOLDER_NAMES:
			return DeviceViewMode.GRID
		if name in LIST_FOLDER_NAMES:
			return DeviceViewMode.LIST
	return None


def parse_device_view_memory(raw: object) -> DeviceViewMemory:
	"""Re-validate a stored ``device_picker_views`` value.

	Accepts a JSON object ``{path: mode}`` whose key order is least → most recently set. Bad entries
	(un-normalizable path, unknown mode) are dropped one by one; anything that is not an object yields
	``EMPTY_VIEW_MEMORY``. Keeps at most
	the ``DEVICE_VIEW_MEMORY_MAX`` most recent entries. Never raises.
	"""
	if not isinstance(raw, Mapping):
		return EMPTY_VIEW_MEMORY
	valid: dict[str, DeviceViewMode] = {}
	for key, value in raw.items():
		if not isinstance(key, str) or not isinstance(value, str):
			continue
		try:
			mode = DeviceViewMode(value)
			normalized = normalize_browse_path(key)
		except (ValueError, DeviceBrowseError):
			continue
		if normalized == key:
			valid[key] = mode
	return dict(list(valid.items())[-DEVICE_VIEW_MEMORY_MAX:])


def dump_device_view_memory(memory: DeviceViewMemory) -> dict[str, str]:
	"""JSON form of ``memory`` (``{path: mode}``, oldest first) — the inverse of ``parse_device_view_memory``."""
	return {path: mode.value for path, mode in memory.items()}


def remember_view(memory: DeviceViewMemory, path: str, setting: DeviceViewSetting) -> DeviceViewMemory:
	"""New memory after the user picks ``setting`` for ``path`` (already normalized).

	``LIST`` / ``GRID`` sets the entry and makes it the most recent, dropping the least recently set entries
	beyond ``DEVICE_VIEW_MEMORY_MAX``; ``AUTO`` removes it (a missing entry is not an error). Pure.
	"""
	updated = {key: mode for key, mode in memory.items() if key != path}
	if setting is not DeviceViewSetting.AUTO:
		updated[path] = DeviceViewMode(setting.value)
	return dict(list(updated.items())[-DEVICE_VIEW_MEMORY_MAX:])


def view_hints(path: str, memory: DeviceViewMemory) -> DeviceViewHints:
	"""``folder_view(path)`` plus the stored choice for exactly ``path``."""
	return DeviceViewHints(folder_view=folder_view(path), stored_view=memory.get(path))


__all__ = [
	"AUTO_GRID_MIN_MEDIA",
	"AUTO_GRID_MIN_RATIO",
	"DEVICE_VIEW_MEMORY_MAX",
	"EMPTY_VIEW_MEMORY",
	"GRID_FOLDER_NAMES",
	"LIST_FOLDER_NAMES",
	"DeviceFolderCounts",
	"DeviceViewHints",
	"DeviceViewMemory",
	"DeviceViewMode",
	"DeviceViewSetting",
	"dump_device_view_memory",
	"folder_counts",
	"folder_view",
	"is_media_name",
	"parse_device_view_memory",
	"remember_view",
	"view_hints",
]
