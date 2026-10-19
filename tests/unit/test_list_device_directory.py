import pytest
from tests.unit.fakes import FakeDeviceRepository

from spacemaker.application.list_device_directory import ListDeviceDirectory
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind, DeviceEntry


def test_given_root_when_list_then_one_device_call_and_sorted() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree[""] = [DeviceEntry("notes.txt", False, 2048), DeviceEntry("DCIM", True), DeviceEntry("Android", True)]
	use_case = ListDeviceDirectory(devices)
	# when
	page = use_case.execute("dev1", "")
	# then
	assert [e.name for e in page.entries] == ["Android", "DCIM", "notes.txt"]
	assert devices.list_directory_calls == [""]
	assert page.path == ""
	assert page.total == 3


def test_given_prefixed_path_when_list_then_adapter_gets_storage_relative() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree["Download"] = [DeviceEntry("report.pdf", False, 10)]
	use_case = ListDeviceDirectory(devices)
	# when
	page = use_case.execute("dev1", "/sdcard/Download/")
	# then
	assert devices.list_directory_calls == ["Download"]
	assert page.path == "Download"


def test_given_escaping_path_when_list_then_invalid_and_no_device_call() -> None:
	# given
	devices = FakeDeviceRepository()
	use_case = ListDeviceDirectory(devices)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.execute("dev1", "../data")
	assert exc.value.kind is DeviceBrowseErrorKind.INVALID_PATH
	assert devices.list_directory_calls == []


def test_given_big_folder_when_list_with_cursor_then_pages_without_recursion() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree["DCIM/Camera"] = [DeviceEntry(f"IMG_{i:05d}.jpg", False, 1) for i in range(3412)]
	use_case = ListDeviceDirectory(devices)
	# when
	first = use_case.execute("dev1", "DCIM/Camera")
	rest = use_case.execute("dev1", "DCIM/Camera", cursor=500, limit=10_000)
	# then
	assert len(first.entries) == 500
	assert first.total == 3412
	assert len(rest.entries) == 2912
	assert set(devices.list_directory_calls) == {"DCIM/Camera"}


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
	use_case = ListDeviceDirectory(devices)
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		use_case.execute("dev1", "Android/data")
	assert exc.value.kind is kind
