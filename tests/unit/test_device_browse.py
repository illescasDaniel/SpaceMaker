import pytest

from spacemaker.domain.device_browse import (
	BROWSE_PAGE_SIZE,
	DeviceBrowseError,
	DeviceBrowseErrorKind,
	DeviceEntry,
	normalize_browse_path,
	page_entries,
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


def test_given_many_entries_when_page_then_cursor_walks_all_pages() -> None:
	# given
	entries = [DeviceEntry(f"f{i:05d}.jpg", False, size=i) for i in range(1200)]
	# when
	first = page_entries("DCIM/Camera", entries)
	second = page_entries("DCIM/Camera", entries, cursor=first.next_cursor or 0)
	last = page_entries("DCIM/Camera", entries, cursor=second.next_cursor or 0)
	# then
	assert len(first.entries) == BROWSE_PAGE_SIZE
	assert first.total == 1200
	assert first.next_cursor == BROWSE_PAGE_SIZE
	assert len(second.entries) == BROWSE_PAGE_SIZE
	assert len(last.entries) == 200
	assert last.next_cursor is None


def test_given_hidden_names_when_is_hidden_then_dot_prefix_only() -> None:
	# given
	# when
	# then
	assert DeviceEntry(".thumbnails", True).is_hidden
	assert not DeviceEntry("DCIM", True).is_hidden
