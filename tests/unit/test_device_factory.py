from spacemaker.adapters.outbound.device.adb_repository import AdbDeviceRepository
from spacemaker.adapters.outbound.device.afc_repository import AfcDeviceRepository
from spacemaker.adapters.outbound.device.factory import device_repository_for
from spacemaker.adapters.outbound.device.mtp_repository import MtpDeviceRepository
from spacemaker.domain.connection import ConnectionMethod


def test_given_mtp_when_device_repository_for_then_mtp_repo():
	repo = device_repository_for(ConnectionMethod.MTP)
	assert isinstance(repo, MtpDeviceRepository)


def test_given_afc_when_device_repository_for_then_afc_repo():
	repo = device_repository_for(ConnectionMethod.AFC)
	assert isinstance(repo, AfcDeviceRepository)


def test_given_adb_when_device_repository_for_then_adb_repo(tmp_path, monkeypatch):
	adb = tmp_path / "adb"
	adb.write_text("#!/bin/sh\n", encoding="utf-8")
	adb.chmod(0o755)
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tmp_path))
	repo = device_repository_for(ConnectionMethod.ADB)
	assert isinstance(repo, AdbDeviceRepository)
