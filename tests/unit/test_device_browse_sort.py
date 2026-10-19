import base64

import pytest

from spacemaker.domain.device_browse import (
	DEFAULT_BROWSE_SORT,
	DeviceBrowseError,
	DeviceBrowseErrorKind,
	DeviceBrowseQuery,
	DeviceBrowseSort,
	DeviceBrowseSortKey,
	DeviceEntry,
	SortOrder,
	decode_sorted_cursor,
	encode_sorted_cursor,
	entry_order_key,
	parse_device_browse_sort,
	scroll_page,
)


NAME_ASC = DeviceBrowseSort(DeviceBrowseSortKey.NAME, SortOrder.ASC)
NAME_DESC = DeviceBrowseSort(DeviceBrowseSortKey.NAME, SortOrder.DESC)
NEWEST = DeviceBrowseSort(DeviceBrowseSortKey.MTIME, SortOrder.DESC)
OLDEST = DeviceBrowseSort(DeviceBrowseSortKey.MTIME, SortOrder.ASC)
LARGEST = DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.DESC)
SMALLEST = DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.ASC)
ALL_SORTS = [NAME_ASC, NAME_DESC, NEWEST, OLDEST, LARGEST, SMALLEST]


def _names(sort: DeviceBrowseSort, entries: list[DeviceEntry]) -> list[str]:
	return [e.name for e in scroll_page("p", entries, DeviceBrowseQuery(sort=sort, limit=500)).entries]


def _walk(entries: list[DeviceEntry], sort: DeviceBrowseSort, limit: int = 100) -> list[str]:
	names: list[str] = []
	cursor: str | None = None
	while True:
		page = scroll_page("p", entries, DeviceBrowseQuery(cursor=cursor, limit=limit, sort=sort))
		names += [e.name for e in page.entries]
		cursor = page.next_cursor
		if cursor is None:
			return names


def _root() -> list[DeviceEntry]:
	return [
		DeviceEntry("notes.txt", False, size=2048, mtime=300),
		DeviceEntry("Download", True, mtime=500),
		DeviceEntry("big.apk", False, size=48_000_000, mtime=100),
		DeviceEntry("Alarms", True, mtime=100),
		DeviceEntry("DCIM", True, mtime=900),
		DeviceEntry("tiny.txt", False, size=1, mtime=200),
	]


@pytest.mark.parametrize(
	("key", "order", "expected"),
	[
		("name", "asc", NAME_ASC),
		("name", "desc", NAME_DESC),
		("mtime", "desc", NEWEST),
		("size", "asc", SMALLEST),
	],
)
def test_given_known_values_when_parse_sort_then_sort(key: str, order: str, expected: DeviceBrowseSort) -> None:
	# given
	# when
	result = parse_device_browse_sort(key, order)
	# then
	assert result == expected


@pytest.mark.parametrize(
	("key", "order"),
	[("type", "asc"), ("name", "up"), (None, "asc"), ("name", None), ("NAME", "asc"), (1, "asc"), ("", "")],
)
def test_given_unknown_values_when_parse_sort_then_none(key: object, order: object) -> None:
	# given
	# when
	result = parse_device_browse_sort(key, order)
	# then
	assert result is None


def test_given_no_sort_when_scroll_then_default_name_order_and_echoed() -> None:
	# given
	entries = _root()
	# when
	page = scroll_page("p", entries, DeviceBrowseQuery())
	# then
	assert [e.name for e in page.entries] == ["Alarms", "DCIM", "Download", "big.apk", "notes.txt", "tiny.txt"]
	assert page.sort == DEFAULT_BROWSE_SORT
	assert DEFAULT_BROWSE_SORT == NAME_ASC


@pytest.mark.parametrize(
	("sort", "expected"),
	[
		(NAME_DESC, ["Download", "DCIM", "Alarms", "tiny.txt", "notes.txt", "big.apk"]),
		(NEWEST, ["DCIM", "Download", "Alarms", "notes.txt", "tiny.txt", "big.apk"]),
		(OLDEST, ["Alarms", "Download", "DCIM", "big.apk", "tiny.txt", "notes.txt"]),
		(LARGEST, ["Alarms", "DCIM", "Download", "big.apk", "notes.txt", "tiny.txt"]),
		(SMALLEST, ["Alarms", "DCIM", "Download", "tiny.txt", "notes.txt", "big.apk"]),
	],
)
def test_given_sort_when_scroll_then_folders_first_and_key_order(sort: DeviceBrowseSort, expected: list[str]) -> None:
	# given
	entries = _root()
	# when
	page = scroll_page("p", entries, DeviceBrowseQuery(sort=sort))
	# then
	assert [e.name for e in page.entries] == expected
	assert page.sort == sort


@pytest.mark.parametrize("sort", [NEWEST, OLDEST, LARGEST, SMALLEST])
def test_given_equal_keys_when_sorted_either_way_then_ties_by_name_ascending(sort: DeviceBrowseSort) -> None:
	# given
	entries = [
		DeviceEntry("b.jpg", False, size=10, mtime=50),
		DeviceEntry("A.jpg", False, size=10, mtime=50),
		DeviceEntry("c.jpg", False, size=10, mtime=50),
	]
	# when
	names = _names(sort, entries)
	# then
	assert names == ["A.jpg", "b.jpg", "c.jpg"]


def test_given_names_equal_ignoring_case_when_name_desc_then_whole_order_reversed() -> None:
	# given
	entries = [DeviceEntry("a", False), DeviceEntry("A", False), DeviceEntry("b", False)]
	# when
	ascending = _names(NAME_ASC, entries)
	descending = _names(NAME_DESC, entries)
	# then
	assert ascending == ["A", "a", "b"]
	assert descending == ["b", "a", "A"]


def test_given_unknown_mtime_when_sorted_by_date_then_counts_as_oldest() -> None:
	# given
	entries = [DeviceEntry("dated.jpg", False, mtime=1_700_000_000), DeviceEntry("unknown.jpg", False, mtime=0)]
	# when
	newest = _names(NEWEST, entries)
	oldest = _names(OLDEST, entries)
	# then
	assert newest == ["dated.jpg", "unknown.jpg"]
	assert oldest == ["unknown.jpg", "dated.jpg"]


@pytest.mark.parametrize("sort", ALL_SORTS)
def test_given_entries_when_order_key_then_sorted_matches_scroll_page(sort: DeviceBrowseSort) -> None:
	# given
	entries = _root()
	# when
	ordered = [e.name for e in sorted(entries, key=entry_order_key(sort))]
	# then
	assert ordered == _names(sort, entries)


def _reference_order(entries: list[DeviceEntry], sort: DeviceBrowseSort) -> list[str]:
	"""Spec ordering written independently of the domain: folders first, key in order, ties by name A→Z."""
	desc = sort.order is SortOrder.DESC
	folders = [e for e in entries if e.is_dir]
	files = [e for e in entries if not e.is_dir]

	def by_name(group: list[DeviceEntry], reverse: bool) -> list[DeviceEntry]:
		return sorted(group, key=lambda e: (e.name.casefold(), e.name), reverse=reverse)

	def by_number(group: list[DeviceEntry], field: str) -> list[DeviceEntry]:
		named = by_name(group, reverse=False)
		return sorted(named, key=lambda e: getattr(e, field), reverse=desc)  # stable: name ties stay A→Z

	if sort.key is DeviceBrowseSortKey.NAME:
		ordered = by_name(folders, desc) + by_name(files, desc)
	elif sort.key is DeviceBrowseSortKey.MTIME:
		ordered = by_number(folders, "mtime") + by_number(files, "mtime")
	else:
		ordered = by_name(folders, reverse=False) + by_number(files, "size")
	return [e.name for e in ordered]


@pytest.mark.parametrize("sort", ALL_SORTS)
def test_given_3412_files_sharing_dates_when_paged_under_sort_then_each_once_in_sort_order(
	sort: DeviceBrowseSort,
) -> None:
	# given
	entries = [
		DeviceEntry(
			f"IMG_{20260000 + i}.jpg",
			False,
			size=3_000_000 + (i % 7) * 200_000,
			mtime=1_754_000_000 + (i % 28) * 86_400,
		)
		for i in range(1, 3413)
	]
	entries += [DeviceEntry(f"Album{i:02d}", True, mtime=i % 3) for i in range(12)]
	# when
	walked = _walk(entries, sort, limit=100)
	# then
	assert len(set(walked)) == len(walked) == len(entries)
	assert walked == _reference_order(entries, sort)


def test_given_entry_inserted_before_cursor_under_newest_when_continue_then_no_duplicate_or_skip() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False, mtime=1000 - i) for i in range(30)]
	first = scroll_page("p", entries, DeviceBrowseQuery(limit=10, sort=NEWEST))
	changed = [*entries, DeviceEntry("brand-new", False, mtime=5000), DeviceEntry("f005b", False, mtime=995)]
	# when
	second = scroll_page("p", changed, DeviceBrowseQuery(cursor=first.next_cursor, limit=100, sort=NEWEST))
	# then
	assert [e.name for e in first.entries] == [f"f{i:03d}" for i in range(10)]
	assert [e.name for e in second.entries] == [f"f{i:03d}" for i in range(10, 30)]


@pytest.mark.parametrize("name", ["a", "Zoë", "line\nbreak", "日本語 file.txt", 'q"uo/te\\', "x" * 300])
@pytest.mark.parametrize("sort", [NAME_ASC, NEWEST, SMALLEST])
def test_given_entry_when_sorted_cursor_round_trip_then_anchor_restored(name: str, sort: DeviceBrowseSort) -> None:
	# given
	entry = DeviceEntry(name, False, size=1234, mtime=1_700_000_000)
	# when
	anchor = decode_sorted_cursor(encode_sorted_cursor(entry, sort), sort)
	# then
	assert sorted([anchor, entry], key=entry_order_key(sort)) == [anchor, entry]
	assert entry_order_key(sort)(anchor) == entry_order_key(sort)(entry)
	assert (anchor.name, anchor.is_dir) == (entry.name, entry.is_dir)


def test_given_entry_when_encode_sorted_cursor_then_url_safe_and_v2() -> None:
	# given
	# when
	cursor = encode_sorted_cursor(DeviceEntry("a/b+c", False, 9, 9), NEWEST)
	# then
	assert cursor.startswith("v2.")
	assert all(ch.isalnum() or ch in "-_.=" for ch in cursor)


@pytest.mark.parametrize(("issued", "requested"), [(NAME_ASC, NEWEST), (NEWEST, OLDEST), (LARGEST, NAME_DESC)])
def test_given_cursor_from_another_sort_when_decode_then_invalid_cursor(
	issued: DeviceBrowseSort, requested: DeviceBrowseSort
) -> None:
	# given
	cursor = encode_sorted_cursor(DeviceEntry("a.jpg", False, 1, 1), issued)
	# when
	# then
	with pytest.raises(DeviceBrowseError) as exc:
		decode_sorted_cursor(cursor, requested)
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR


@pytest.mark.parametrize("raw", ["", "garbage", "5", "v2.", "v2.!!!", "v2.bm90LWpzb24", "v2.e30", "v2.WzEsMiwzXQ"])
def test_given_foreign_cursor_when_decode_sorted_then_invalid_cursor(raw: str) -> None:
	# given
	# when
	# then
	with pytest.raises(DeviceBrowseError) as exc:
		decode_sorted_cursor(raw, NAME_ASC)
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR


def test_given_cursor_issued_before_sorting_revision_when_scroll_then_invalid_cursor() -> None:
	# given
	v1_cursor = "v1." + base64.urlsafe_b64encode(b'[true,"a.jpg","a.jpg"]').decode()
	# when
	# then
	with pytest.raises(DeviceBrowseError) as exc:
		scroll_page("p", _root(), DeviceBrowseQuery(cursor=v1_cursor))
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR


def test_given_page_cursor_reused_with_another_sort_when_scroll_then_invalid_cursor() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False, mtime=i) for i in range(30)]
	first = scroll_page("p", entries, DeviceBrowseQuery(limit=10, sort=NAME_ASC))
	# when
	# then
	with pytest.raises(DeviceBrowseError) as exc:
		scroll_page("p", entries, DeviceBrowseQuery(cursor=first.next_cursor, limit=10, sort=NEWEST))
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR


def test_given_more_pages_when_scroll_then_next_cursor_is_v2() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False) for i in range(30)]
	# when
	page = scroll_page("p", entries, DeviceBrowseQuery(limit=10))
	# then
	assert page.next_cursor is not None
	assert page.next_cursor.startswith("v2.")
