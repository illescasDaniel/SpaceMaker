import pytest

from spacemaker.domain.device_browse import (
	DeviceBrowseError,
	DeviceBrowseErrorKind,
	DeviceBrowseQuery,
	DeviceEntry,
	normalize_browse_path,
	scroll_page,
	sort_entries,
)


@pytest.mark.parametrize(
	("raw", "expected"),
	[
		("", ""),
		("/", ""),
		("DCIM/Camera", "DCIM/Camera"),
		("/DCIM/Camera/", "DCIM/Camera"),
		("/sdcard/Download", "Download"),
		("storage/emulated/0/WhatsApp/Media", "WhatsApp/Media"),
		("/storage/self/primary", ""),
		("résumé dir/a b", "résumé dir/a b"),
	],
)
def test_given_path_when_normalize_then_storage_relative(raw: str, expected: str) -> None:
	# given
	# when
	result = normalize_browse_path(raw)
	# then
	assert result == expected


@pytest.mark.parametrize("raw", ["../etc", "DCIM/../../x", "a/\x00b", "/sdcard/../data", "..", "a\\..\\b"])
def test_given_escaping_path_when_normalize_then_invalid(raw: str) -> None:
	# given
	# when
	# then
	with pytest.raises(DeviceBrowseError) as exc:
		normalize_browse_path(raw)
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_PATH


def test_given_mixed_entries_when_sort_then_folders_first_case_insensitive() -> None:
	# given
	entries = [
		DeviceEntry("b.txt", False),
		DeviceEntry("Zeta", True),
		DeviceEntry("a.txt", False),
		DeviceEntry("alpha", True),
	]
	# when
	names = [e.name for e in sort_entries(entries)]
	# then
	assert names == ["alpha", "Zeta", "a.txt", "b.txt"]


def _mixed_entries(count: int = 250) -> list[DeviceEntry]:
	entries = [DeviceEntry(f"Dir{i:03d}", True) for i in range(count // 5)]
	entries += [DeviceEntry(f"file{i:04d}.jpg" if i % 2 else f"File{i:04d}.JPG", False, size=i) for i in range(count)]
	return entries


def _walk(entries: list[DeviceEntry], limit: int = 100, query: str = "", show_hidden: bool = False) -> list[list[str]]:
	pages: list[list[str]] = []
	cursor: str | None = None
	while True:
		page = scroll_page(
			"p", entries, DeviceBrowseQuery(cursor=cursor, limit=limit, query=query, show_hidden=show_hidden)
		)
		pages.append([e.name for e in page.entries])
		cursor = page.next_cursor
		if cursor is None:
			return pages


def test_given_bad_cursor_when_scroll_then_invalid_cursor() -> None:
	# given
	# when
	# then
	with pytest.raises(DeviceBrowseError) as exc:
		scroll_page("p", _mixed_entries(), DeviceBrowseQuery(cursor="12"))
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR


def test_given_250_mixed_entries_when_scroll_then_each_entry_once_in_folder_first_order() -> None:
	# given
	entries = _mixed_entries(250)
	# when
	pages = _walk(entries, limit=100)
	# then
	flat = [n for page in pages for n in page]
	assert [len(p) for p in pages] == [100, 100, 100]
	assert flat == [e.name for e in sort_entries(entries)]
	assert len(set(flat)) == len(entries)
	assert flat[0].startswith("Dir")


def test_given_last_page_when_scroll_then_next_cursor_none_and_totals() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False) for i in range(150)]
	# when
	first = scroll_page("p", entries, DeviceBrowseQuery(limit=100))
	last = scroll_page("p", entries, DeviceBrowseQuery(cursor=first.next_cursor, limit=100))
	# then
	assert first.next_cursor is not None
	assert len(last.entries) == 50
	assert last.next_cursor is None
	assert last.total == 150
	assert last.total_unfiltered == 150
	assert last.path == "p"


def test_given_exactly_limit_entries_when_scroll_then_single_page() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False) for i in range(100)]
	# when
	page = scroll_page("p", entries, DeviceBrowseQuery(limit=100))
	# then
	assert len(page.entries) == 100
	assert page.next_cursor is None


def test_given_entry_inserted_before_cursor_when_continue_then_no_duplicate_or_skip() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False) for i in range(30)]
	first = scroll_page("p", entries, DeviceBrowseQuery(limit=10))
	changed = [*entries, DeviceEntry("a-new", False), DeviceEntry("f005b", False)]
	# when
	second = scroll_page("p", changed, DeviceBrowseQuery(cursor=first.next_cursor, limit=100))
	# then
	assert [e.name for e in second.entries] == [f"f{i:03d}" for i in range(10, 30)]


def test_given_cursor_entry_deleted_when_continue_then_resumes_after_its_position() -> None:
	# given
	entries = [DeviceEntry(f"f{i:03d}", False) for i in range(30)]
	first = scroll_page("p", entries, DeviceBrowseQuery(limit=10))
	remaining = [e for e in entries if e.name != "f009"]
	# when
	second = scroll_page("p", remaining, DeviceBrowseQuery(cursor=first.next_cursor, limit=100))
	# then
	assert [e.name for e in second.entries] == [f"f{i:03d}" for i in range(10, 30)]


def test_given_query_when_scroll_then_case_insensitive_substring_and_counts() -> None:
	# given
	entries = [
		DeviceEntry("IMG_001.jpg", False),
		DeviceEntry("holiday", True),
		DeviceEntry("img_002.PNG", False),
		DeviceEntry("notes.txt", False),
	]
	# when
	page = scroll_page("p", entries, DeviceBrowseQuery(query="IMG"))
	# then
	assert [e.name for e in page.entries] == ["IMG_001.jpg", "img_002.PNG"]
	assert page.total == 2
	assert page.total_unfiltered == 4


def test_given_hidden_entries_when_scroll_then_excluded_unless_show_hidden() -> None:
	# given
	entries = [DeviceEntry(".thumbnails", True), DeviceEntry("DCIM", True), DeviceEntry(".nomedia", False)]
	# when
	default = scroll_page("p", entries, DeviceBrowseQuery())
	shown = scroll_page("p", entries, DeviceBrowseQuery(show_hidden=True))
	# then
	assert [e.name for e in default.entries] == ["DCIM"]
	assert default.total == 1
	assert default.total_unfiltered == 3
	assert [e.name for e in shown.entries] == [".thumbnails", "DCIM", ".nomedia"]
	assert shown.total == 3


def test_given_filter_and_paging_when_scroll_then_cursor_walks_filtered_set() -> None:
	# given
	entries = [DeviceEntry(f"match{i:03d}", False) for i in range(25)] + [DeviceEntry("other", False)]
	# when
	pages = _walk(entries, limit=10, query="MATCH")
	# then
	assert [len(p) for p in pages] == [10, 10, 5]


def test_given_hidden_names_when_is_hidden_then_dot_prefix_only() -> None:
	# given
	# when
	# then
	assert DeviceEntry(".thumbnails", True).is_hidden
	assert not DeviceEntry("DCIM", True).is_hidden
