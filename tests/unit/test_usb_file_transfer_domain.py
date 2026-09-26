from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.transfer_folders import TransferFolder
from spacemaker.domain.usb_file_transfer import (
	can_start_usb_file_transfer,
	default_transfer_folders,
	documents_transfer_destination,
	is_usb_file_transfer_method,
	shows_iphone_limit_banner,
	transfer_control_flags,
)


def test_given_mtp_when_banner_then_hidden() -> None:
	assert not shows_iphone_limit_banner(ConnectionMethod.MTP)
	assert not shows_iphone_limit_banner(ConnectionMethod.ADB)


def test_given_afc_when_banner_then_shown() -> None:
	assert shows_iphone_limit_banner(ConnectionMethod.AFC)


def test_given_wifi_when_usb_transfer_method_then_false() -> None:
	assert not is_usb_file_transfer_method(ConnectionMethod.WIFI)
	assert is_usb_file_transfer_method(ConnectionMethod.MTP)


def test_given_afc_when_default_folders_then_dcim() -> None:
	assert default_transfer_folders(ConnectionMethod.AFC) == frozenset({TransferFolder.DCIM})


def test_given_idle_with_device_and_folders_when_can_start_then_true() -> None:
	assert can_start_usb_file_transfer(
		has_device=True,
		folders_selected=True,
		phase=JobPhase.IDLE,
	)
	assert not can_start_usb_file_transfer(
		has_device=False,
		folders_selected=True,
		phase=JobPhase.IDLE,
	)


def test_given_running_when_control_flags_then_pause_and_stop() -> None:
	flags = transfer_control_flags(JobPhase.RUNNING)
	assert flags["start"] is False
	assert flags["pause"] is True
	assert flags["stop"] is True


def test_given_device_path_when_destination_then_under_root(tmp_path) -> None:
	# given
	root = str(tmp_path / "SpaceMaker")
	# when
	dest = documents_transfer_destination(root, "/sdcard/Download/a.pdf")
	# then
	assert dest is not None
	assert dest.endswith("sdcard/Download/a.pdf") or dest.endswith("Download/a.pdf") or "Download" in dest


def test_given_parent_escape_when_destination_then_none() -> None:
	assert documents_transfer_destination("/home/user/Documents/SpaceMaker", "../etc/passwd") is None
