from pathlib import Path

from tests.unit.fakes import FakeDeviceRepository, FakeFileSystem

from spacemaker.application.transfer_usb_files import TransferUsbFiles
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.library import TransferMode
from spacemaker.domain.transfer_folders import TransferFolder
from spacemaker.ports.outbound.device_repository import DeviceInfo


def test_given_pdf_in_download_when_transfer_copy_then_lands_in_documents(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.devices = [DeviceInfo(device_id="dev1", label="Pixel")]
	devices.file_paths = ["/sdcard/Download/report.pdf", "/sdcard/DCIM/photo.jpg"]
	devices.sizes["/sdcard/Download/report.pdf"] = 200
	devices.sizes["/sdcard/DCIM/photo.jpg"] = 100
	dest_root = str(tmp_path / "SpaceMaker")
	use_case = TransferUsbFiles(devices, fs)
	# when
	result = use_case.run(
		dest_root,
		"dev1",
		TransferMode.COPY,
		folders=frozenset({TransferFolder.DOWNLOAD}),
	)
	# then
	assert result.completed == 1
	assert len(devices.pulled) == 1
	assert devices.pulled[0][1] == "/sdcard/Download/report.pdf"
	assert devices.deleted == []
	assert any(path.endswith("report.pdf") for path in fs.files)


def test_given_move_mode_when_transfer_then_deletes_on_device(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = ["/sdcard/Documents/notes.txt"]
	devices.sizes["/sdcard/Documents/notes.txt"] = 40
	use_case = TransferUsbFiles(devices, fs)
	# when
	use_case.run(
		str(tmp_path / "SpaceMaker"),
		"dev1",
		TransferMode.MOVE,
		folders=frozenset({TransferFolder.DOCUMENTS}),
	)
	# then
	assert devices.deleted == [("dev1", "/sdcard/Documents/notes.txt")]


def test_given_existing_same_size_when_transfer_then_skips_pull(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = ["/sdcard/Download/a.pdf"]
	devices.sizes["/sdcard/Download/a.pdf"] = 500
	dest_root = str(tmp_path / "SpaceMaker")
	dest = str(Path(dest_root) / "sdcard" / "Download" / "a.pdf")
	fs.files[dest] = 500
	use_case = TransferUsbFiles(devices, fs)
	# when
	result = use_case.run(
		dest_root,
		"dev1",
		TransferMode.COPY,
		folders=frozenset({TransferFolder.DOWNLOAD}),
	)
	# then
	assert result.completed == 1
	assert devices.pulled == []


def test_given_empty_folders_when_transfer_then_noop(tmp_path: Path) -> None:
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = ["/sdcard/Download/a.pdf"]
	use_case = TransferUsbFiles(devices, fs)
	result = use_case.run(
		str(tmp_path / "SpaceMaker"),
		"dev1",
		TransferMode.COPY,
		folders=frozenset(),
	)
	assert result.total == 0
	assert devices.pulled == []


def test_given_stop_when_after_file_then_ends_queue(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = [
		"/sdcard/Download/a.pdf",
		"/sdcard/Download/b.pdf",
	]
	devices.sizes["/sdcard/Download/a.pdf"] = 10
	devices.sizes["/sdcard/Download/b.pdf"] = 20
	control = ExtractJobControl()
	use_case = TransferUsbFiles(devices, fs)

	def on_progress(progress) -> None:
		if progress.completed == 1:
			control.request_stop()

	# when
	result = use_case.run(
		str(tmp_path / "SpaceMaker"),
		"dev1",
		TransferMode.COPY,
		folders=frozenset({TransferFolder.DOWNLOAD}),
		control=control,
		on_progress=on_progress,
	)
	# then
	assert result.completed == 1
	assert len(devices.pulled) == 1
	assert control.was_stopped()
