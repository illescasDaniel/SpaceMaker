from __future__ import annotations

import base64
import binascii
import bisect
import json
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cmp_to_key
from typing import Any, Protocol, cast

from spacemaker.domain.device_media import is_media_name
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


class DeviceBrowseSortKey(StrEnum):
	"""Column the picker sorts by. Folders are always listed before files whatever the key."""

	NAME = "name"
	MTIME = "mtime"
	SIZE = "size"


class SortOrder(StrEnum):
	ASC = "asc"
	DESC = "desc"


@dataclass(frozen=True, slots=True)
class DeviceBrowseSort:
	"""Picker listing order (folders first, then ``key`` in ``order``).

	Ties under ``MTIME`` / ``SIZE`` fall back to name A→Z in both directions; under ``NAME`` / ``DESC``
	the whole name order (exact-name tie-break included) is reversed. ``mtime`` 0 (unknown) counts as
	the oldest. Under ``SIZE`` folders (no size) are ordered by name A→Z.
	"""

	key: DeviceBrowseSortKey = DeviceBrowseSortKey.NAME
	order: SortOrder = SortOrder.ASC


DEFAULT_BROWSE_SORT = DeviceBrowseSort()
"""Name, A→Z — first run, after Clear preferences, or a corrupt stored value."""


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
	sort: DeviceBrowseSort = DEFAULT_BROWSE_SORT
	"""The effective order of ``entries`` (echoed to the client)."""
	entry_count: int = 0
	"""Grid view: entries after the hidden rule, ignoring ``query`` (folders + files)."""
	media_count: int = 0
	"""Grid view: of those, files with a previewable photo/video extension."""


@dataclass(frozen=True, slots=True)
class DeviceBrowseQuery:
	"""Scroll-page request. Bounds: ``limit`` 1..``BROWSE_PAGE_MAX``; ``query`` at most ``BROWSE_QUERY_MAX`` chars.

	``cursor`` is an opaque token from a previous page; ``refresh`` bypasses the listing cache.
	``sort`` ``None`` means "use the stored picker preference" (resolved by the use case before paging).
	"""

	cursor: str | None = None
	limit: int = BROWSE_SCROLL_PAGE_SIZE
	query: str = ""
	show_hidden: bool = False
	refresh: bool = False
	sort: DeviceBrowseSort | None = None


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
	"""Folders first, then case-insensitive name (the default order)."""
	return sorted(entries, key=entry_order_key(DEFAULT_BROWSE_SORT))


def parse_device_browse_sort(key: object, order: object) -> DeviceBrowseSort | None:
	"""``DeviceBrowseSort`` from raw values (request body or stored preference); ``None`` if either is not
	a known ``DeviceBrowseSortKey`` / ``SortOrder`` value. Never raises.
	"""
	if not isinstance(key, str) or not isinstance(order, str):
		return None
	try:
		return DeviceBrowseSort(DeviceBrowseSortKey(key), SortOrder(order))
	except ValueError:
		return None


class OrderKey(Protocol):
	"""A sort key ``sorted`` / ``bisect`` can compare (tuple or ``functools.cmp_to_key`` object)."""

	def __lt__(self, other: Any, /) -> bool: ...


def _compare(a: DeviceEntry, b: DeviceEntry, sort: DeviceBrowseSort) -> int:
	if a.is_dir != b.is_dir:
		return -1 if a.is_dir else 1
	name_a = (a.name.casefold(), a.name)
	name_b = (b.name.casefold(), b.name)
	name_cmp = (name_a > name_b) - (name_a < name_b)
	sign = -1 if sort.order is SortOrder.DESC else 1
	if sort.key is DeviceBrowseSortKey.NAME:
		return sign * name_cmp
	if sort.key is DeviceBrowseSortKey.SIZE and a.is_dir:
		return name_cmp
	left, right = (a.mtime, b.mtime) if sort.key is DeviceBrowseSortKey.MTIME else (a.size, b.size)
	number_cmp = (left > right) - (left < right)
	return sign * number_cmp if number_cmp else name_cmp


def entry_order_key(sort: DeviceBrowseSort) -> Callable[[DeviceEntry], OrderKey]:
	"""Sort key implementing ``sort`` as a total order (see ``DeviceBrowseSort``), usable with
	``sorted`` and ``bisect`` so keyset paging neither skips nor duplicates entries.
	"""
	return cast(Callable[[DeviceEntry], OrderKey], cmp_to_key(lambda a, b: _compare(a, b, sort)))


_SORTED_CURSOR_PREFIX = "v2."


def encode_sorted_cursor(entry: DeviceEntry, sort: DeviceBrowseSort) -> str:
	"""Opaque, URL-safe ``v2.`` cursor encoding ``sort`` and the ordering fields of the last returned ``entry``."""
	payload = json.dumps(
		{
			"k": sort.key.value,
			"o": sort.order.value,
			"n": entry.name,
			"d": entry.is_dir,
			"s": entry.size,
			"m": entry.mtime,
		},
		separators=(",", ":"),
		ensure_ascii=False,
	)
	return _SORTED_CURSOR_PREFIX + base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _is_int(value: object) -> bool:
	return isinstance(value, int) and not isinstance(value, bool)


def decode_sorted_cursor(text: str, sort: DeviceBrowseSort) -> DeviceEntry:
	"""The anchor entry of a ``v2.`` cursor; paging continues strictly after it under ``sort``.

	Raises ``DeviceBrowseError(INVALID_CURSOR)`` for anything this module did not issue, a ``v1.`` cursor,
	or a cursor issued under a different ``sort``.
	"""
	invalid = DeviceBrowseError(DeviceBrowseErrorKind.INVALID_CURSOR, "invalid cursor")
	if not text.startswith(_SORTED_CURSOR_PREFIX):
		raise invalid
	try:
		raw = base64.b64decode(text[len(_SORTED_CURSOR_PREFIX) :].encode("ascii"), altchars=b"-_", validate=True)
		data = json.loads(raw.decode("utf-8"))
	except (ValueError, binascii.Error, UnicodeError) as exc:
		raise invalid from exc
	if not isinstance(data, dict):
		raise invalid
	name, is_dir, size, mtime = data.get("n"), data.get("d"), data.get("s"), data.get("m")
	if (
		parse_device_browse_sort(data.get("k"), data.get("o")) != sort
		or not isinstance(name, str)
		or not isinstance(is_dir, bool)
		or not _is_int(size)
		or not _is_int(mtime)
	):
		raise invalid
	return DeviceEntry(name, is_dir, cast(int, size), cast(int, mtime))


@dataclass(frozen=True, slots=True)
class DeviceFolderCounts:
	"""Page-1 counts over the cached listing: hidden rule applied, filter ``query`` ignored.

	``entry_count`` = folders + files; ``media_count`` = files whose extension is a previewable photo or video.
	"""

	entry_count: int
	media_count: int


def folder_counts(entries: Iterable[DeviceEntry], *, show_hidden: bool) -> DeviceFolderCounts:
	"""Count ``entries`` for auto-detection; dot-entries count only when ``show_hidden``. Folders are never media."""
	entry_total = 0
	media_total = 0
	for entry in entries:
		if entry.is_hidden and not show_hidden:
			continue
		entry_total += 1
		if not entry.is_dir and is_media_name(entry.name):
			media_total += 1
	return DeviceFolderCounts(entry_count=entry_total, media_count=media_total)


def scroll_page(path: str, entries: Sequence[DeviceEntry], request: DeviceBrowseQuery) -> DeviceDirectoryScrollPage:
	"""Sort ``entries``, drop hidden ones unless ``show_hidden``, keep case-insensitive substring matches of
	``request.query``, then return up to ``request.limit`` entries strictly after ``request.cursor``.

	``total`` = filtered count, ``total_unfiltered`` = ``len(entries)``. Raises
	``DeviceBrowseError(INVALID_CURSOR)`` for a bad cursor.

	Orders by ``request.sort`` (``None`` → ``DEFAULT_BROWSE_SORT``) via
	``entry_order_key``, pages with ``encode_sorted_cursor`` / ``decode_sorted_cursor`` and sets ``page.sort``.
	"""
	sort = request.sort or DEFAULT_BROWSE_SORT
	key = entry_order_key(sort)
	counts = folder_counts(entries, show_hidden=request.show_hidden)
	after = decode_sorted_cursor(request.cursor, sort) if request.cursor is not None else None
	needle = request.query.casefold()
	visible = [
		e for e in entries if (request.show_hidden or not e.is_hidden) and (not needle or needle in e.name.casefold())
	]
	ordered = sorted(visible, key=key)
	start = 0
	if after is not None:
		start = bisect.bisect_right(ordered, key(after), key=key)
	window = ordered[start : start + request.limit]
	has_more = start + request.limit < len(ordered)
	return DeviceDirectoryScrollPage(
		path=path,
		entries=tuple(window),
		total=len(ordered),
		total_unfiltered=len(entries),
		next_cursor=encode_sorted_cursor(window[-1], sort) if has_more and window else None,
		sort=sort,
		entry_count=counts.entry_count,
		media_count=counts.media_count,
	)


__all__ = [
	"BROWSE_PAGE_MAX",
	"BROWSE_QUERY_MAX",
	"BROWSE_SCROLL_PAGE_SIZE",
	"DEFAULT_BROWSE_SORT",
	"DeviceBrowseError",
	"DeviceBrowseErrorKind",
	"DeviceBrowseQuery",
	"DeviceBrowseSort",
	"DeviceBrowseSortKey",
	"DeviceDirectoryScrollPage",
	"DeviceEntry",
	"DeviceFolderCounts",
	"OrderKey",
	"SortOrder",
	"decode_sorted_cursor",
	"encode_sorted_cursor",
	"entry_order_key",
	"folder_counts",
	"normalize_browse_path",
	"parse_device_browse_sort",
	"scroll_page",
	"sort_entries",
]
