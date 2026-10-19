from __future__ import annotations

import base64
import binascii
import bisect
import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.transfer_folders import strip_android_user_storage_prefix


BROWSE_SCROLL_PAGE_SIZE = 100
BROWSE_PAGE_MAX = 500
BROWSE_QUERY_MAX = 200


class DeviceBrowseErrorKind(StrEnum):
	"""Why a single directory listing failed (maps to the picker's state panels)."""

	INVALID_PATH = "invalid_path"
	PERMISSION_DENIED = "permission_denied"
	UNAUTHORIZED = "unauthorized"
	UNPLUGGED = "unplugged"
	TIMEOUT = "timeout"
	NOT_FOUND = "not_found"
	FAILED = "failed"
	INVALID_CURSOR = "invalid_cursor"


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
class DeviceDirectoryScrollPage:
	"""One keyset-paginated slice of a filtered, sorted listing.

	``total`` is the filtered count; ``total_unfiltered`` counts every entry (hidden included).
	``next_cursor`` is ``None`` on the last page.
	"""

	path: str
	entries: tuple[DeviceEntry, ...]
	total: int
	total_unfiltered: int
	next_cursor: str | None


@dataclass(frozen=True, slots=True)
class DeviceBrowseQuery:
	"""Scroll-page request. Bounds: ``limit`` 1..``BROWSE_PAGE_MAX``; ``query`` at most ``BROWSE_QUERY_MAX`` chars.

	``cursor`` is an opaque token from a previous page; ``refresh`` bypasses the listing cache.
	"""

	cursor: str | None = None
	limit: int = BROWSE_SCROLL_PAGE_SIZE
	query: str = ""
	show_hidden: bool = False
	refresh: bool = False


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


def browse_sort_key(entry: DeviceEntry) -> tuple[bool, str, str]:
	"""Total order for listings: folders first, then case-insensitive name, then exact name."""
	return (not entry.is_dir, entry.name.casefold(), entry.name)


def sort_entries(entries: list[DeviceEntry]) -> list[DeviceEntry]:
	"""Folders first, then case-insensitive name."""
	return sorted(entries, key=browse_sort_key)


_CURSOR_PREFIX = "v1."


def encode_browse_cursor(entry: DeviceEntry) -> str:
	"""Opaque, URL-safe cursor encoding the sort key of the last returned ``entry``."""
	payload = json.dumps(list(browse_sort_key(entry)), separators=(",", ":"), ensure_ascii=False)
	return _CURSOR_PREFIX + base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def decode_browse_cursor(text: str) -> tuple[bool, str, str]:
	"""Inverse of ``encode_browse_cursor`` (a ``browse_sort_key`` tuple).

	Raises ``DeviceBrowseError(INVALID_CURSOR)`` for anything this module did not issue.
	"""
	invalid = DeviceBrowseError(DeviceBrowseErrorKind.INVALID_CURSOR, "invalid cursor")
	if not text.startswith(_CURSOR_PREFIX):
		raise invalid
	try:
		raw = base64.b64decode(text[len(_CURSOR_PREFIX) :].encode("ascii"), altchars=b"-_", validate=True)
		data = json.loads(raw.decode("utf-8"))
	except (ValueError, binascii.Error, UnicodeError) as exc:
		raise invalid from exc
	if (
		not isinstance(data, list)
		or len(data) != 3
		or not isinstance(data[0], bool)
		or not isinstance(data[1], str)
		or not isinstance(data[2], str)
	):
		raise invalid
	return (data[0], data[1], data[2])


def scroll_page(path: str, entries: Sequence[DeviceEntry], request: DeviceBrowseQuery) -> DeviceDirectoryScrollPage:
	"""Sort ``entries``, drop hidden ones unless ``show_hidden``, keep case-insensitive substring matches of
	``request.query``, then return up to ``request.limit`` entries strictly after ``request.cursor``.

	``total`` = filtered count, ``total_unfiltered`` = ``len(entries)``. Raises
	``DeviceBrowseError(INVALID_CURSOR)`` for a bad cursor.
	"""
	after = decode_browse_cursor(request.cursor) if request.cursor is not None else None
	needle = request.query.casefold()
	visible = [
		e for e in entries if (request.show_hidden or not e.is_hidden) and (not needle or needle in e.name.casefold())
	]
	ordered = sorted(visible, key=browse_sort_key)
	start = 0
	if after is not None:
		start = bisect.bisect_right(ordered, after, key=browse_sort_key)
	window = ordered[start : start + request.limit]
	has_more = start + request.limit < len(ordered)
	return DeviceDirectoryScrollPage(
		path=path,
		entries=tuple(window),
		total=len(ordered),
		total_unfiltered=len(entries),
		next_cursor=encode_browse_cursor(window[-1]) if has_more and window else None,
	)


__all__ = [
	"BROWSE_PAGE_MAX",
	"BROWSE_QUERY_MAX",
	"BROWSE_SCROLL_PAGE_SIZE",
	"DeviceBrowseError",
	"DeviceBrowseErrorKind",
	"DeviceBrowseQuery",
	"DeviceDirectoryScrollPage",
	"DeviceEntry",
	"browse_sort_key",
	"decode_browse_cursor",
	"encode_browse_cursor",
	"normalize_browse_path",
	"scroll_page",
	"sort_entries",
]
