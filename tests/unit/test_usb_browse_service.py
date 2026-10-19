from __future__ import annotations

from tests.unit.fakes import FakeDeviceRepository

from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceEntry


def _services(devices: FakeDeviceRepository) -> AppServices:
	services = AppServices(port=8765, bind_host="127.0.0.1")
	services._device_repos[ConnectionMethod.ADB] = devices
	with services.session._lock:
		services.session.active_module = AppModule.USB_FILE_TRANSFER
	return services


def test_given_root_with_download_and_documents_when_snapshot_then_one_listing_and_presets() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree[""] = [DeviceEntry("Download", True), DeviceEntry("Documents", True), DeviceEntry("a.txt", False)]
	services = _services(devices)
	# when
	snap = services._usb_browse_snapshot(ConnectionMethod.ADB, "dev1")
	# then
	assert devices.list_directory_calls == [""]
	assert snap["picker_available"] is True
	assert snap["available_folders"] == ["documents", "download"]


def test_given_no_device_when_snapshot_then_picker_unavailable_with_hint_and_no_listing() -> None:
	# given
	devices = FakeDeviceRepository()
	services = _services(devices)
	# when
	snap = services._usb_browse_snapshot(ConnectionMethod.ADB, "")
	# then
	assert snap["picker_available"] is False
	assert "authorized device" in str(snap["hint"])
	assert devices.list_directory_calls == []


def test_given_extract_extras_when_leave_home_then_cleared() -> None:
	# given
	services = _services(FakeDeviceRepository())
	services.set_extract_extra_paths(["WhatsApp/Media"])
	# when
	services.leave_module_for_home()
	# then
	assert services.session.extract_extra_paths == []
