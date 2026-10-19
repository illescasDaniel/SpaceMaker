import pytest
from tests.unit.fakes import FakeDeviceRepository, FakeUserPreferences
from tests.unit.passcode_fakes import FakeClock

from spacemaker.application.device_listing_cache import DeviceListingCache
from spacemaker.application.list_device_directory import ListDeviceDirectory
from spacemaker.domain.device_browse import (
	DEFAULT_BROWSE_SORT,
	DeviceBrowseError,
	DeviceBrowseErrorKind,
	DeviceBrowseQuery,
	DeviceBrowseSort,
	DeviceBrowseSortKey,
	DeviceEntry,
	SortOrder,
)


NAME_ASC = DeviceBrowseSort(DeviceBrowseSortKey.NAME, SortOrder.ASC)
NEWEST = DeviceBrowseSort(DeviceBrowseSortKey.MTIME, SortOrder.DESC)
LARGEST = DeviceBrowseSort(DeviceBrowseSortKey.SIZE, SortOrder.DESC)


def _cached(devices: FakeDeviceRepository, preferences: FakeUserPreferences | None = None) -> ListDeviceDirectory:
	return ListDeviceDirectory(devices, cache=DeviceListingCache(FakeClock()), preferences=preferences)


def _files(devices: FakeDeviceRepository) -> None:
	devices.tree[""] = [
		DeviceEntry("a.txt", False, size=10, mtime=300),
		DeviceEntry("b.txt", False, size=5000, mtime=100),
		DeviceEntry("c.txt", False, size=200, mtime=900),
	]


def test_given_root_when_scroll_then_one_device_call_and_sorted() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree[""] = [DeviceEntry("notes.txt", False, 2048), DeviceEntry("DCIM", True), DeviceEntry("Android", True)]
	use_case = _cached(devices)
	# when
	page = use_case.scroll("adb", "dev1", "", DeviceBrowseQuery())
	# then
	assert [e.name for e in page.entries] == ["Android", "DCIM", "notes.txt"]
	assert devices.list_directory_calls == [""]
	assert page.path == ""
	assert page.total == 3


def test_given_prefixed_path_when_scroll_then_adapter_gets_storage_relative() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree["Download"] = [DeviceEntry("report.pdf", False, 10)]
	use_case = _cached(devices)
	# when
	page = use_case.scroll("adb", "dev1", "/sdcard/Download/", DeviceBrowseQuery())
	# then
	assert devices.list_directory_calls == ["Download"]
	assert page.path == "Download"


def test_given_escaping_path_when_scroll_then_invalid_and_no_device_call() -> None:
	# given
	devices = FakeDeviceRepository()
	use_case = _cached(devices)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.scroll("adb", "dev1", "../data", DeviceBrowseQuery())
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_PATH
	assert devices.list_directory_calls == []


def test_given_big_folder_when_two_pages_then_single_device_listing() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree["DCIM/Camera"] = [DeviceEntry(f"IMG_{i:05d}.jpg", False, 1) for i in range(3412)]
	use_case = _cached(devices)
	# when
	first = use_case.scroll("adb", "dev1", "DCIM/Camera", DeviceBrowseQuery(limit=100))
	second = use_case.scroll("adb", "dev1", "DCIM/Camera", DeviceBrowseQuery(cursor=first.next_cursor, limit=500))
	# then
	assert len(first.entries) == 100
	assert first.total == 3412
	assert len(second.entries) == 500
	assert second.entries[0].name == "IMG_00100.jpg"
	assert devices.list_directory_calls == ["DCIM/Camera"]


def test_given_refresh_when_scroll_then_listing_reloaded() -> None:
	# given
	devices = FakeDeviceRepository()
	use_case = _cached(devices)
	use_case.scroll("adb", "dev1", "", DeviceBrowseQuery())
	# when
	use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(refresh=True))
	# then
	assert devices.list_directory_calls == ["", ""]


def test_given_bad_cursor_when_scroll_then_invalid_cursor_and_no_device_call() -> None:
	# given
	devices = FakeDeviceRepository()
	use_case = _cached(devices)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.scroll("adb", "dev1", "DCIM", DeviceBrowseQuery(cursor="nonsense"))
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR
	assert devices.list_directory_calls == []


def test_given_no_cache_when_scroll_twice_then_device_called_each_time() -> None:
	# given
	devices = FakeDeviceRepository()
	use_case = ListDeviceDirectory(devices)
	# when
	use_case.scroll("adb", "dev1", "", DeviceBrowseQuery())
	use_case.scroll("adb", "dev1", "", DeviceBrowseQuery())
	# then
	assert devices.list_directory_calls == ["", ""]


@pytest.mark.parametrize(
	"kind",
	[
		DeviceBrowseErrorKind.PERMISSION_DENIED,
		DeviceBrowseErrorKind.UNAUTHORIZED,
		DeviceBrowseErrorKind.UNPLUGGED,
		DeviceBrowseErrorKind.TIMEOUT,
	],
)
def test_given_device_error_when_list_then_error_kind_propagates(kind: DeviceBrowseErrorKind) -> None:
	# given
	devices = FakeDeviceRepository()
	devices.browse_errors["Android/data"] = kind
	use_case = _cached(devices)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.scroll("adb", "dev1", "Android/data", DeviceBrowseQuery())
	assert exc.value.kind is kind


def test_given_stored_size_desc_and_no_request_sort_when_scroll_then_largest_first_and_no_write() -> None:
	# given
	devices = FakeDeviceRepository()
	_files(devices)
	prefs = FakeUserPreferences(device_picker_sort=LARGEST)
	use_case = _cached(devices, prefs)
	# when
	page = use_case.scroll("adb", "dev1", "", DeviceBrowseQuery())
	# then
	assert [e.name for e in page.entries] == ["b.txt", "c.txt", "a.txt"]
	assert page.sort == LARGEST
	assert prefs.picker_sort_writes == []


def test_given_no_preferences_object_and_no_request_sort_when_scroll_then_default_sort() -> None:
	# given
	devices = FakeDeviceRepository()
	_files(devices)
	use_case = _cached(devices)
	# when
	page = use_case.scroll("adb", "dev1", "", DeviceBrowseQuery())
	# then
	assert page.sort == DEFAULT_BROWSE_SORT
	assert [e.name for e in page.entries] == ["a.txt", "b.txt", "c.txt"]


def test_given_explicit_sort_differing_from_stored_when_scroll_then_saved_once() -> None:
	# given
	devices = FakeDeviceRepository()
	_files(devices)
	prefs = FakeUserPreferences(device_picker_sort=LARGEST)
	use_case = _cached(devices, prefs)
	# when
	page = use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(sort=NEWEST))
	# then
	assert [e.name for e in page.entries] == ["c.txt", "a.txt", "b.txt"]
	assert prefs.picker_sort_writes == [NEWEST]


def test_given_explicit_sort_equal_to_stored_when_scroll_then_no_write() -> None:
	# given
	devices = FakeDeviceRepository()
	_files(devices)
	prefs = FakeUserPreferences(device_picker_sort=NEWEST)
	use_case = _cached(devices, prefs)
	# when
	use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(sort=NEWEST))
	# then
	assert prefs.picker_sort_writes == []


def test_given_explicit_sort_and_device_error_when_scroll_then_nothing_saved() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.browse_errors["Android/data"] = DeviceBrowseErrorKind.PERMISSION_DENIED
	prefs = FakeUserPreferences()
	use_case = _cached(devices, prefs)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.scroll("adb", "dev1", "Android/data", DeviceBrowseQuery(sort=NEWEST))
	assert exc.value.kind is DeviceBrowseErrorKind.PERMISSION_DENIED
	assert prefs.picker_sort_writes == []


def _first_page_cursor(devices: FakeDeviceRepository) -> str:
	devices.tree[""] = [DeviceEntry(f"f{i:03d}.txt", False, size=i, mtime=i) for i in range(5)]
	cursor = _cached(devices).scroll("adb", "dev1", "", DeviceBrowseQuery(limit=2, sort=NAME_ASC)).next_cursor
	assert cursor is not None
	devices.list_directory_calls.clear()
	return cursor


def test_given_cursor_from_other_sort_when_scroll_then_invalid_cursor_and_no_device_call() -> None:
	# given
	devices = FakeDeviceRepository()
	cursor = _first_page_cursor(devices)
	use_case = _cached(devices, FakeUserPreferences())
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(cursor=cursor, sort=NEWEST))
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR
	assert devices.list_directory_calls == []


def test_given_cursor_and_stored_sort_differs_when_scroll_without_sort_then_invalid_cursor() -> None:
	# given
	devices = FakeDeviceRepository()
	cursor = _first_page_cursor(devices)
	prefs = FakeUserPreferences(device_picker_sort=NEWEST)
	use_case = _cached(devices, prefs)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(cursor=cursor))
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_CURSOR
	assert devices.list_directory_calls == []
	assert prefs.picker_sort_writes == []


def test_given_two_pages_under_size_sort_when_sort_changes_then_single_device_call() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree[""] = [DeviceEntry(f"f{i:03d}.txt", False, size=i, mtime=i) for i in range(5)]
	use_case = _cached(devices, FakeUserPreferences())
	first = use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(limit=2, sort=LARGEST))
	use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(limit=2, cursor=first.next_cursor, sort=LARGEST))
	# when
	page = use_case.scroll("adb", "dev1", "", DeviceBrowseQuery(limit=2, sort=NEWEST))
	# then
	assert [e.name for e in page.entries] == ["f004.txt", "f003.txt"]
	assert devices.list_directory_calls == [""]
