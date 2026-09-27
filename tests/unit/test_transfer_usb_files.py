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
	dest = str(Path(dest_root) / "Download" / "a.pdf")
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


def test_given_extra_folder_when_transfer_then_includes_nested(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = [
		"WhatsApp/Media/a.jpg",
		"Download/b.pdf",
		"other/c.txt",
	]
	devices.sizes["WhatsApp/Media/a.jpg"] = 10
	devices.sizes["Download/b.pdf"] = 20
	devices.sizes["other/c.txt"] = 30
	use_case = TransferUsbFiles(devices, fs)
	# when
	result = use_case.run(
		str(tmp_path / "SpaceMaker"),
		"dev1",
		TransferMode.COPY,
		folders=frozenset(),
		extra_paths=frozenset({"WhatsApp/Media"}),
	)
	# then
	assert result.completed == 1
	assert devices.pulled[0][1] == "WhatsApp/Media/a.jpg"


def test_given_mount_relative_extra_when_absolute_adb_paths_then_includes(tmp_path: Path) -> None:
	# given — Browse stores mount-relative extras; ADB lists absolute paths
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = [
		"/sdcard/WhatsApp/Media/voice/a.opus",
		"/storage/emulated/0/WhatsApp/Media/b.jpg",
		"/sdcard/Download/c.pdf",
	]
	devices.sizes["/sdcard/WhatsApp/Media/voice/a.opus"] = 10
	devices.sizes["/storage/emulated/0/WhatsApp/Media/b.jpg"] = 20
	devices.sizes["/sdcard/Download/c.pdf"] = 30
	use_case = TransferUsbFiles(devices, fs)
	# when
	result = use_case.run(
		str(tmp_path / "SpaceMaker"),
		"dev1",
		TransferMode.COPY,
		folders=frozenset(),
		extra_paths=frozenset({"WhatsApp/Media"}),
	)
	# then
	assert result.completed == 2
	pulled = {item[1] for item in devices.pulled}
	assert pulled == {
		"/sdcard/WhatsApp/Media/voice/a.opus",
		"/storage/emulated/0/WhatsApp/Media/b.jpg",
	}


def test_given_presets_and_extra_file_when_transfer_then_union(tmp_path: Path) -> None:
	# given
	fs = FakeFileSystem()
	devices = FakeDeviceRepository()
	devices.bind_filesystem(fs)
	devices.file_paths = [
		"/sdcard/Download/a.pdf",
		"/sdcard/notes.txt",
	]
	devices.sizes["/sdcard/Download/a.pdf"] = 10
	devices.sizes["/sdcard/notes.txt"] = 5
	use_case = TransferUsbFiles(devices, fs)
	# when
	result = use_case.run(
		str(tmp_path / "SpaceMaker"),
		"dev1",
		TransferMode.COPY,
		folders=frozenset({TransferFolder.DOWNLOAD}),
		extra_paths=frozenset({"notes.txt"}),
	)
	# then
	assert result.completed == 2
	pulled = {item[1] for item in devices.pulled}
	assert pulled == {"/sdcard/Download/a.pdf", "/sdcard/notes.txt"}
	assert any(path.endswith("Download/a.pdf") for path in fs.files)
	assert any(path.endswith("notes.txt") and "sdcard" not in path for path in fs.files)


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
