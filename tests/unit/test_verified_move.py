from __future__ import annotations

from pathlib import Path

import pytest
from tests.unit.fakes import FakeDeviceRepository, FakeFileSystem

from spacemaker.application.extract_media import ExtractMedia
from spacemaker.application.transfer_usb_files import TransferUsbFiles
from spacemaker.application.verified_move import PullVerificationError
from spacemaker.domain.library import TransferMode
from spacemaker.domain.transfer_folders import TransferFolder


class _TruncatingDevices(FakeDeviceRepository):
	"""Pretends the transfer was cut short: only half the bytes reach the host."""

	def pull_file(self, device_id: str, device_path: str, local_path: str) -> None:
		self.pulled.append((device_id, device_path, local_path))
		self.files_set(local_path, self.sizes[device_path] // 2)


def test_given_truncated_pull_when_extract_move_then_device_file_kept_and_partial_removed() -> None:
	# given
	fs = FakeFileSystem()
	devices = _TruncatingDevices()
	devices.bind_filesystem(fs)
	devices.media_paths = ["/sdcard/DCIM/Camera/a.jpg"]
	devices.sizes["/sdcard/DCIM/Camera/a.jpg"] = 1000
	use_case = ExtractMedia(devices, fs)
	# when / then
	with pytest.raises(PullVerificationError):
		use_case.run("/lib", "dev1", TransferMode.MOVE)
	assert devices.deleted == []
	assert not any(path.endswith("a.jpg") for path in fs.files)


def test_given_truncated_pull_when_usb_transfer_move_then_device_file_kept(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = _TruncatingDevices()
	devices.bind_filesystem(fs)
	devices.file_paths = ["/sdcard/Documents/notes.txt"]
	devices.sizes["/sdcard/Documents/notes.txt"] = 40
	use_case = TransferUsbFiles(devices, fs)
	# when / then
	with pytest.raises(PullVerificationError):
		use_case.run(
			str(tmp_path / "SpaceMaker"),
			"dev1",
			TransferMode.MOVE,
			folders=frozenset({TransferFolder.DOCUMENTS}),
		)
	assert devices.deleted == []


def test_given_unknown_remote_size_when_extract_move_then_device_file_kept() -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.media_paths = ["/sdcard/DCIM/Camera/a.jpg"]
	use_case = ExtractMedia(devices, fs)
	# when
	use_case.run("/lib", "dev1", TransferMode.MOVE)
	# then
	assert devices.deleted == []
