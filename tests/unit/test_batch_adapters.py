import zipfile
from pathlib import Path

import pytest

from spacemaker.adapters.outbound.filesystem.send2trash_trash import SystemTrash
from spacemaker.adapters.outbound.filesystem.shutil_disk_space import ShutilDiskSpace
from spacemaker.adapters.outbound.filesystem.zip_archive_writer import StoredZipArchiveWriter
from spacemaker.domain.gallery_batch import ArchiveEntry, TrashError


def test_given_files_when_write_zip_then_entries_stored_with_given_names(tmp_path) -> None:
	# given
	first = tmp_path / "one.bin"
	second = tmp_path / "two.bin"
	first.write_bytes(b"1" * 10)
	second.write_bytes(b"2" * 20)
	destination = tmp_path / "out" / "x.zip"
	# when
	StoredZipArchiveWriter().write_stored_zip(
		str(destination),
		[ArchiveEntry(str(first), "2025/a.avif.jpg"), ArchiveEntry(str(second), "b.mp4")],
	)
	# then
	with zipfile.ZipFile(destination) as archive:
		assert archive.namelist() == ["2025/a.avif.jpg", "b.mp4"]
		assert all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist())
		assert archive.read("b.mp4") == b"2" * 20


def test_given_missing_source_when_write_zip_then_no_partial_or_final_file(tmp_path) -> None:
	# given
	destination = tmp_path / "out" / "x.zip"
	# when
	# then
	with pytest.raises(FileNotFoundError):
		StoredZipArchiveWriter().write_stored_zip(
			str(destination), [ArchiveEntry(str(tmp_path / "gone.bin"), "gone.bin")]
		)
	assert list((tmp_path / "out").iterdir()) == []


def test_given_missing_path_when_free_bytes_then_uses_nearest_existing_ancestor(tmp_path) -> None:
	# given
	missing = tmp_path / "a" / "b" / "c"
	# when
	free = ShutilDiskSpace().free_bytes(str(missing))
	# then
	assert free > 0


def test_given_trash_backend_error_when_move_then_trash_error_and_file_untouched(tmp_path, monkeypatch) -> None:
	# given
	target = tmp_path / "keep.jpg"
	target.write_bytes(b"x")

	def boom(_path: str) -> None:
		raise OSError("no trash here")

	monkeypatch.setattr("spacemaker.adapters.outbound.filesystem.send2trash_trash.send2trash", boom)
	# when
	# then
	with pytest.raises(TrashError):
		SystemTrash().move_to_trash(str(target))
	assert Path(target).read_bytes() == b"x"
