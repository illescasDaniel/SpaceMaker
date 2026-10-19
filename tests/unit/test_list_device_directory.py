import pytest
from tests.unit.fakes import FakeDeviceRepository
from tests.unit.passcode_fakes import FakeClock

from spacemaker.application.device_listing_cache import DeviceListingCache
from spacemaker.application.list_device_directory import ListDeviceDirectory
from spacemaker.domain.device_browse import (
	DeviceBrowseError,
	DeviceBrowseErrorKind,
	DeviceBrowseQuery,
	DeviceEntry,
)


def _cached(devices: FakeDeviceRepository) -> ListDeviceDirectory:
	return ListDeviceDirectory(devices, cache=DeviceListingCache(FakeClock()))


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
