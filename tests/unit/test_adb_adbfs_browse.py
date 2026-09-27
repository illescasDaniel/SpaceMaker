from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from spacemaker.adapters.outbound.device.adb_repository import AdbDeviceRepository
from spacemaker.domain.transfer_folders import TransferFolder


def test_given_test_mount_when_browse_root_then_path(tmp_path: Path) -> None:
	# given
	mount = tmp_path / "phone"
	mount.mkdir()
	repo = AdbDeviceRepository(Path("/usr/bin/adb"), test_mounts={"serial": mount})
	# when / then
	assert repo.browse_root("serial") == str(mount.resolve())
	assert repo.browse_root("other") is None


def test_given_adbfs_ok_when_browse_root_then_mounts(tmp_path: Path, monkeypatch) -> None:
	# given
	monkeypatch.setattr("spacemaker.adapters.outbound.device.adb_repository.sys.platform", "linux")
	calls: list[list[str]] = []
	envs: list[dict[str, str]] = []

	def fake_which(name: str) -> str | None:
		if name == "adbfs":
			return "/usr/bin/adbfs"
		if name in {"fusermount3", "fusermount", "umount"}:
			return f"/usr/bin/{name}"
		return None

	def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN003
		calls.append(list(cmd))
		env = kwargs.get("env") or {}
		envs.append(dict(env))
		assert kwargs.get("timeout") is not None
		return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

	repo = AdbDeviceRepository(
		tmp_path / "adb",
		which=fake_which,
		run=fake_run,
	)
	# when
	root = repo.browse_root("PIXELSERIAL")
	# then
	assert root is not None
	assert Path(root).is_dir()
	assert calls
	assert calls[0][0] == "/usr/bin/adbfs"
	assert envs[0].get("ANDROID_SERIAL") == "PIXELSERIAL"
	assert repo._live_mounts.get("PIXELSERIAL") is not None
	assert repo.peek_browse_root("PIXELSERIAL") == root
	assert repo.browse_backend_available() is True
	repo.release_mounts()
	assert not repo._live_mounts


def test_given_no_adbfs_when_browse_backend_then_false(tmp_path: Path, monkeypatch) -> None:
	# given
	monkeypatch.setattr("spacemaker.adapters.outbound.device.adb_repository.sys.platform", "linux")
	repo = AdbDeviceRepository(tmp_path / "adb", which=lambda _n: None)
	# when / then
	assert repo.browse_backend_available() is False
	assert repo.browse_root("serial") is None
	assert repo.peek_browse_root("serial") is None


def test_given_shell_dirs_when_probe_then_download(tmp_path: Path) -> None:
	# given
	device = MagicMock()
	device.shell.side_effect = lambda cmd: "yes\n" if "/sdcard/Download" in cmd else ""
	client = MagicMock()
	client.device.return_value = device
	repo = AdbDeviceRepository(tmp_path / "adb")
	repo._client = client
	# when
	found = repo.probe_existing_transfer_folders("serial")
	# then
	assert TransferFolder.DOWNLOAD in found


def test_given_extra_folder_when_list_extra_then_finds_under_sdcard(tmp_path: Path) -> None:
	# given
	device = MagicMock()

	def shell(cmd: str) -> str:
		if ' -f "/sdcard/WhatsApp/Media"' in cmd and " -d " in cmd:
			return "dir\n"
		if cmd.startswith('find "/sdcard/WhatsApp/Media"'):
			return "/sdcard/WhatsApp/Media/a.jpg\n/sdcard/WhatsApp/Media/b.txt\n"
		return "missing\n"

	device.shell.side_effect = shell
	client = MagicMock()
	client.device.return_value = device
	repo = AdbDeviceRepository(tmp_path / "adb")
	repo._client = client
	repo._mount_device_roots["serial"] = "/sdcard"
	# when
	found = repo.list_extra_file_paths("serial", frozenset({"WhatsApp/Media"}))
	# then
	assert found == [
		"/sdcard/WhatsApp/Media/a.jpg",
		"/sdcard/WhatsApp/Media/b.txt",
	]
