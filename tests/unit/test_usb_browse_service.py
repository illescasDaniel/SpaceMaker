from __future__ import annotations

import os
from concurrent.futures import Future
from pathlib import Path

import pytest
from tests.unit.fakes import FakeDeviceRepository

from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseQuery, DeviceEntry
from spacemaker.domain.jobs import JobPhase


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


def test_given_root_with_150_folders_when_snapshot_then_late_preset_still_found() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree[""] = [DeviceEntry(f"Aaa{i:03d}", True) for i in range(150)] + [DeviceEntry("Download", True)]
	services = _services(devices)
	# when
	snap = services._usb_browse_snapshot(ConnectionMethod.ADB, "dev1")
	# then
	assert snap["available_folders"] == ["download"]


def test_given_probe_then_picker_open_of_root_when_within_ttl_then_one_device_listing() -> None:
	# given
	devices = FakeDeviceRepository()
	devices.tree[""] = [DeviceEntry("Download", True), DeviceEntry("a.txt", False)]
	services = _services(devices)
	services._usb_browse_snapshot(ConnectionMethod.ADB, "dev1")
	# when
	page = services.list_device_directory(ConnectionMethod.ADB, "dev1", "", DeviceBrowseQuery())
	# then
	assert [e.name for e in page.entries] == ["Download", "a.txt"]
	assert devices.list_directory_calls == [""]


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


def _ready_to_transfer(services: AppServices) -> None:
	with services.session._lock:
		services.session.device_id = "dev1"
		services.session.connection_method = ConnectionMethod.ADB
		services.session.transfer_extra_paths = ["a.txt"]


def test_given_unwritable_destination_when_start_transfer_then_error_and_no_job(tmp_path: Path) -> None:
	# given
	locked = tmp_path / "locked"
	locked.mkdir()
	locked.chmod(0o500)
	services = _services(FakeDeviceRepository())
	_ready_to_transfer(services)
	services.set_usb_transfer_destination(str(locked))
	try:
		if os.access(locked, os.W_OK):
			pytest.skip("directory permissions are not enforced for this user")
		# when
		services.start_usb_transfer()
		# then
		assert services.session.usb_transfer_phase is JobPhase.ERROR
		assert "Cannot use destination folder" in services.session.last_error
		assert services._usb_transfer_future is None
	finally:
		locked.chmod(0o700)


def test_given_destination_is_a_file_when_start_transfer_then_error_and_no_job(tmp_path: Path) -> None:
	# given
	blocker = tmp_path / "file.txt"
	blocker.write_text("x")
	services = _services(FakeDeviceRepository())
	_ready_to_transfer(services)
	services.set_usb_transfer_destination(str(blocker / "sub"))
	# when
	services.start_usb_transfer()
	# then
	assert services.session.usb_transfer_phase is JobPhase.ERROR
	assert services._usb_transfer_future is None


def _busy_services(method: ConnectionMethod = ConnectionMethod.ADB) -> AppServices:
	services = AppServices(port=8765, bind_host="127.0.0.1")
	with services.session._lock:
		services.session.connection_method = method
	return services


def _future(done: bool) -> Future[None]:
	future: Future[None] = Future()
	if done:
		future.set_result(None)
	return future


def test_given_pending_transfer_when_is_busy_on_session_method_then_true() -> None:
	# given
	services = _busy_services()
	services._usb_transfer_future = _future(done=False)
	# when / then
	assert services.is_busy(ConnectionMethod.ADB, "dev1") is True


def test_given_pending_transfer_when_is_busy_on_other_method_then_false() -> None:
	# given
	services = _busy_services()
	services._usb_transfer_future = _future(done=False)
	# when / then
	assert services.is_busy(ConnectionMethod.AFC, "dev1") is False


def test_given_finished_transfer_when_is_busy_then_false() -> None:
	# given
	services = _busy_services()
	services._usb_transfer_future = _future(done=True)
	# when / then
	assert services.is_busy(ConnectionMethod.ADB, "dev1") is False


def test_given_pending_extract_when_is_busy_then_true_and_finished_extract_false() -> None:
	# given
	services = _busy_services()
	services._extract_future = _future(done=False)
	# when / then
	assert services.is_busy(ConnectionMethod.ADB, "dev1") is True
	services._extract_future = _future(done=True)
	assert services.is_busy(ConnectionMethod.ADB, "dev1") is False
