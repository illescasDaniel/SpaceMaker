from __future__ import annotations

from pathlib import Path

from spacemaker.adapters.outbound.device.mount_dirs import remove_empty_mount_dir


def test_given_empty_mount_dir_when_remove_then_directory_is_gone(tmp_path: Path) -> None:
	# given
	mount = tmp_path / "mnt"
	mount.mkdir()
	# when
	remove_empty_mount_dir(mount)
	# then
	assert not mount.exists()


def test_given_mount_dir_with_device_files_when_remove_then_files_are_kept(tmp_path: Path) -> None:
	# given: a still-mounted FUSE dir looks like a non-empty directory
	mount = tmp_path / "mnt"
	(mount / "DCIM").mkdir(parents=True)
	photo = mount / "DCIM" / "a.jpg"
	photo.write_bytes(b"precious")
	# when
	remove_empty_mount_dir(mount)
	# then
	assert photo.read_bytes() == b"precious"


def test_given_missing_dir_when_remove_then_no_error(tmp_path: Path) -> None:
	# given
	missing = tmp_path / "nope"
	# when
	remove_empty_mount_dir(missing)
	# then
	assert not missing.exists()
