from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.transfer_folders import strip_android_user_storage_prefix


BROWSE_PAGE_SIZE = 500


class DeviceBrowseErrorKind(StrEnum):
	"""Why a single directory listing failed (maps to the picker's state panels)."""

	INVALID_PATH = "invalid_path"
	PERMISSION_DENIED = "permission_denied"
	UNAUTHORIZED = "unauthorized"
	UNPLUGGED = "unplugged"
	TIMEOUT = "timeout"
	NOT_FOUND = "not_found"
	FAILED = "failed"


class DeviceBrowseError(Exception):
	def __init__(self, kind: DeviceBrowseErrorKind, detail: str = "") -> None:
		super().__init__(detail or kind.value)
		self.kind = kind
		self.detail = detail


@dataclass(frozen=True, slots=True)
class DeviceEntry:
	"""One child of a device directory. ``mtime`` is epoch seconds, 0 when unknown."""

	name: str
	is_dir: bool
	size: int = 0
	mtime: int = 0

	@property
	def is_hidden(self) -> bool:
		return self.name.startswith(".")


@dataclass(frozen=True, slots=True)
class DeviceDirectoryPage:
	"""One page of a sorted directory listing (folders first, then case-insensitive name)."""

	path: str
	entries: tuple[DeviceEntry, ...]
	total: int
	next_cursor: int | None


def normalize_browse_path(path: str) -> str:
	"""Storage-relative path for the picker (``""`` = Phone storage root).

	Strips Android user-storage prefixes; raises ``DeviceBrowseError(INVALID_PATH)`` for
	NUL bytes or ``..`` segments (backslashes count as separators). Never returns a leading ``/``.
	"""
	if "\x00" in path:
		raise DeviceBrowseError(DeviceBrowseErrorKind.INVALID_PATH, "NUL in path")
	text = path.replace("\\", "/")
	if any(part == ".." for part in text.split("/")):
		raise DeviceBrowseError(DeviceBrowseErrorKind.INVALID_PATH, "path escapes user storage")
	return strip_android_user_storage_prefix(text)


def sort_entries(entries: list[DeviceEntry]) -> list[DeviceEntry]:
	"""Folders first, then case-insensitive name."""
	return sorted(entries, key=lambda e: (not e.is_dir, e.name.casefold(), e.name))


def page_entries(
	path: str, entries: list[DeviceEntry], cursor: int = 0, limit: int = BROWSE_PAGE_SIZE
) -> DeviceDirectoryPage:
	"""Sort ``entries`` and return the ``[cursor, cursor+limit)`` slice."""
	ordered = sort_entries(entries)
	start = max(cursor, 0)
	end = start + max(limit, 1)
	next_cursor = end if end < len(ordered) else None
	return DeviceDirectoryPage(
		path=path, entries=tuple(ordered[start:end]), total=len(ordered), next_cursor=next_cursor
	)


__all__ = [
	"BROWSE_PAGE_SIZE",
	"DeviceBrowseError",
	"DeviceBrowseErrorKind",
	"DeviceDirectoryPage",
	"DeviceEntry",
	"normalize_browse_path",
	"page_entries",
	"sort_entries",
]
