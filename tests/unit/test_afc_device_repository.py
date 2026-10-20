import threading
from collections.abc import Callable
from pathlib import Path

import pytest
from tests.unit.fakes import FakeFileSystem

from spacemaker.adapters.outbound.device.afc_repository import AfcDeviceRepository
from spacemaker.application.extract_media import ExtractMedia
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind
from spacemaker.domain.library import LibraryFolder, TransferMode
from spacemaker.domain.source_folders import SourceFolder


def test_given_dcim_heic_when_list_media_paths_then_lists_relative(tmp_path: Path) -> None:
	dcim = tmp_path / "DCIM" / "100APPLE"
	dcim.mkdir(parents=True)
	(dcim / "IMG_0001.HEIC").write_bytes(b"x" * 64)
	repo = AfcDeviceRepository(test_mounts={"phone-udid": tmp_path})
	paths = repo.list_media_paths("phone-udid")
	assert paths == ["DCIM/100APPLE/IMG_0001.HEIC"]


def test_given_dcim_pdf_when_list_file_paths_then_includes_any_type(tmp_path: Path) -> None:
	# given
	dcim = tmp_path / "DCIM" / "100APPLE"
	dcim.mkdir(parents=True)
	(dcim / "scan.pdf").write_bytes(b"%PDF")
	(dcim / "IMG_0001.HEIC").write_bytes(b"x" * 64)
	repo = AfcDeviceRepository(test_mounts={"phone-udid": tmp_path})
	# when
	paths = repo.list_file_paths("phone-udid")
	# then
	assert "DCIM/100APPLE/scan.pdf" in paths
	assert "DCIM/100APPLE/IMG_0001.HEIC" in paths


def test_given_photodata_when_list_media_paths_then_skips_non_camera_folders(tmp_path: Path) -> None:
	dcim = tmp_path / "DCIM" / "100APPLE"
	dcim.mkdir(parents=True)
	(dcim / "IMG_0001.HEIC").write_bytes(b"x" * 64)
	photo_data = tmp_path / "PhotoData" / "Mutations"
	photo_data.mkdir(parents=True)
	(photo_data / "slow.heic").write_bytes(b"y" * 64)
	repo = AfcDeviceRepository(test_mounts={"phone-udid": tmp_path})
	paths = repo.list_media_paths("phone-udid")
	assert paths == ["DCIM/100APPLE/IMG_0001.HEIC"]


def test_given_100apple_at_mount_root_when_list_media_paths_then_prefixes_dcim(tmp_path: Path) -> None:
	roll = tmp_path / "100APPLE"
	roll.mkdir()
	(roll / "IMG_0001.heic").write_bytes(b"x" * 64)
	repo = AfcDeviceRepository(test_mounts={"phone-udid": tmp_path})
	paths = repo.list_media_paths("phone-udid")
	assert paths == ["DCIM/100APPLE/IMG_0001.heic"]


def test_given_file_when_pull_and_size_then_match(tmp_path: Path) -> None:
	dcim = tmp_path / "DCIM" / "100APPLE"
	dcim.mkdir(parents=True)
	(dcim / "a.mov").write_bytes(b"video-bytes")
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	dest = tmp_path / "out.mov"
	repo.pull_file("udid", "DCIM/100APPLE/a.mov", str(dest))
	assert dest.read_bytes() == b"video-bytes"
	assert repo.remote_file_size("udid", "DCIM/100APPLE/a.mov") == len(b"video-bytes")


def test_given_move_when_delete_device_file_then_removes_source(tmp_path: Path) -> None:
	dcim = tmp_path / "DCIM" / "100APPLE"
	dcim.mkdir(parents=True)
	photo = dcim / "b.heic"
	photo.write_bytes(b"1")
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	repo.delete_device_file("udid", "DCIM/100APPLE/b.heic")
	assert not photo.is_file()


def test_given_afc_mount_when_extract_dcim_then_copies_to_originals(tmp_path: Path) -> None:
	mount = tmp_path / "mount"
	dcim = mount / "DCIM" / "100APPLE"
	dcim.mkdir(parents=True)
	(dcim / "IMG_1.heic").write_bytes(b"heic")
	library = str(tmp_path / "library")
	fs = FakeFileSystem()
	devices = AfcDeviceRepository(test_mounts={"udid": mount})
	use_case = ExtractMedia(devices, fs)
	progress = use_case.run(
		library,
		"udid",
		TransferMode.COPY,
		source_folders=frozenset({SourceFolder.DCIM}),
	)
	assert progress.completed == 1
	dest = fs.library_path(library, LibraryFolder.ORIGINALS, "DCIM/100APPLE/IMG_1.heic")
	assert Path(dest).read_bytes() == b"heic"


def test_given_mount_when_list_directory_then_one_level_with_dirs_and_sizes(tmp_path: Path) -> None:
	# given
	mount = tmp_path / "mnt"
	(mount / "DCIM" / "100APPLE").mkdir(parents=True)
	(mount / "DCIM" / "note.txt").write_bytes(b"abc")
	repo = AfcDeviceRepository(test_mounts={"udid": mount})
	# when
	root = repo.list_directory("udid", "")
	dcim = repo.list_directory("udid", "DCIM")
	# then
	assert [(e.name, e.is_dir) for e in root] == [("DCIM", True)]
	assert {(e.name, e.is_dir, e.size) for e in dcim} == {("100APPLE", True, 0), ("note.txt", False, 3)}


def test_given_missing_directory_when_list_directory_then_not_found(tmp_path: Path) -> None:
	# given
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.list_directory("udid", "Nope")
	assert exc.value.kind is DeviceBrowseErrorKind.NOT_FOUND


def test_given_file_when_stat_file_then_name_size_mtime(tmp_path: Path) -> None:
	# given
	(tmp_path / "DCIM").mkdir()
	(tmp_path / "DCIM" / "IMG_1.HEIC").write_bytes(b"abcd")
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	# when
	entry = repo.stat_file("udid", "DCIM/IMG_1.HEIC")
	# then
	assert (entry.name, entry.is_dir, entry.size) == ("IMG_1.HEIC", False, 4)
	assert entry.mtime > 0


def test_given_missing_file_when_stat_file_then_not_found(tmp_path: Path) -> None:
	# given
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.stat_file("udid", "DCIM/nope.jpg")
	assert exc.value.kind is DeviceBrowseErrorKind.NOT_FOUND


def test_given_big_file_when_read_head_then_only_requested_bytes(tmp_path: Path) -> None:
	# given
	(tmp_path / "a.jpg").write_bytes(b"0123456789")
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	# when
	head = repo.read_head("udid", "a.jpg", 4, 5.0)
	whole = repo.read_head("udid", "a.jpg", 100, 5.0)
	# then
	assert head == b"0123"
	assert whole == b"0123456789"


def test_given_unknown_device_when_read_head_then_unplugged(tmp_path: Path) -> None:
	# given
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.read_head("other", "a.jpg", 4, 5.0)
	assert exc.value.kind is DeviceBrowseErrorKind.UNPLUGGED


def test_given_file_when_pull_file_with_timeout_then_copied(tmp_path: Path) -> None:
	# given
	mount = tmp_path / "mnt"
	mount.mkdir()
	(mount / "a.jpg").write_bytes(b"photo")
	repo = AfcDeviceRepository(test_mounts={"udid": mount})
	dest = tmp_path / "out.jpg"
	# when
	repo.pull_file_with_timeout("udid", "a.jpg", str(dest), 5.0)
	# then
	assert dest.read_bytes() == b"photo"


def test_given_missing_file_when_pull_file_with_timeout_then_not_found(tmp_path: Path) -> None:
	# given
	repo = AfcDeviceRepository(test_mounts={"udid": tmp_path})
	# when / then
	with pytest.raises(DeviceBrowseError) as exc:
		repo.pull_file_with_timeout("udid", "nope.jpg", str(tmp_path / "out.jpg"), 5.0)
	assert exc.value.kind is DeviceBrowseErrorKind.NOT_FOUND


def test_given_timeout_and_caller_deleted_temp_when_late_worker_writes_then_path_not_recreated(tmp_path: Path) -> None:
	# given
	mount = tmp_path / "mnt"
	mount.mkdir()
	(mount / "a.jpg").write_bytes(b"photo")
	repo = AfcDeviceRepository(test_mounts={"udid": mount})
	dest = tmp_path / "out.jpg"
	gate = threading.Event()
	released = threading.Event()

	def hung_bounded(work: Callable[[], None], timeout_s: float) -> None:
		def late() -> None:
			gate.wait()
			try:
				work()
			except ValueError:  # the abandoned handle is closed: the late write is rejected
				pass
			finally:
				released.set()

		threading.Thread(target=late, daemon=True).start()
		raise DeviceBrowseError(DeviceBrowseErrorKind.TIMEOUT)

	repo._bounded = hung_bounded  # type: ignore[method-assign,assignment]
	# when
	with pytest.raises(DeviceBrowseError):
		repo.pull_file_with_timeout("udid", "a.jpg", str(dest), 0.0)
	dest.unlink()
	gate.set()
	assert released.wait(timeout=5)
	# then
	assert not dest.exists()
