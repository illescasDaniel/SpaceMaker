from pathlib import Path

from spacemaker.application.usb_transfer_browse import (
	device_relative_paths_from_host_picks,
	probe_existing_transfer_folders,
)
from spacemaker.domain.transfer_folders import (
	TransferFolder,
	existing_transfer_folders_from_dir_names,
	host_path_to_device_relative,
	merge_extra_paths,
	path_matches_extra_sources,
)


def test_given_dir_names_when_probe_then_matching_presets() -> None:
	# given / when
	found = existing_transfer_folders_from_dir_names(["Download", "DCIM", "foo"])
	# then
	assert TransferFolder.DOWNLOAD in found
	assert TransferFolder.DCIM in found
	assert TransferFolder.MUSIC not in found


def test_given_mount_tree_when_probe_then_finds_download(tmp_path: Path) -> None:
	# given — shallow probe (FUSE-safe): only top-level dirs
	(tmp_path / "Download").mkdir(parents=True)
	(tmp_path / "Other").mkdir(parents=True)
	# when
	found = probe_existing_transfer_folders(tmp_path)
	# then
	assert found == frozenset({TransferFolder.DOWNLOAD})


def test_given_nested_only_when_shallow_probe_then_empty(tmp_path: Path) -> None:
	# given
	(tmp_path / "Phone" / "Download").mkdir(parents=True)
	# when / then — nested Download is not scanned (avoids FUSE hangs)
	assert probe_existing_transfer_folders(tmp_path) == frozenset()


def test_given_host_under_mount_when_relative_then_ok(tmp_path: Path) -> None:
	# given
	target = tmp_path / "WhatsApp" / "Media"
	target.mkdir(parents=True)
	# when
	relative = host_path_to_device_relative(str(tmp_path), str(target))
	# then
	assert relative == "WhatsApp/Media"


def test_given_host_outside_mount_when_relative_then_none(tmp_path: Path) -> None:
	# given
	outside = tmp_path.parent / "elsewhere"
	outside.mkdir(exist_ok=True)
	# when / then
	assert host_path_to_device_relative(str(tmp_path), str(outside)) is None


def test_given_picks_when_convert_then_only_under_mount(tmp_path: Path) -> None:
	# given
	folder = tmp_path / "Docs"
	folder.mkdir()
	file_path = tmp_path / "note.txt"
	file_path.write_text("x", encoding="utf-8")
	outside = tmp_path.parent / "nope.txt"
	outside.write_text("y", encoding="utf-8")
	# when
	accepted = device_relative_paths_from_host_picks(
		str(tmp_path),
		[str(folder), str(file_path), str(outside)],
	)
	# then
	assert accepted == ["Docs", "note.txt"]


def test_given_prefixed_picks_when_convert_then_storage_stripped(tmp_path: Path) -> None:
	# given — full-root adbfs without subdir leaves storage/self/primary in the relative path
	nested = tmp_path / "storage" / "self" / "primary" / "WhatsApp" / "Media"
	nested.mkdir(parents=True)
	file_path = tmp_path / "storage" / "self" / "primary" / "notes.txt"
	file_path.parent.mkdir(parents=True, exist_ok=True)
	file_path.write_text("x", encoding="utf-8")
	# when
	accepted = device_relative_paths_from_host_picks(
		str(tmp_path),
		[str(nested), str(file_path)],
	)
	# then
	assert accepted == ["WhatsApp/Media", "notes.txt"]


def test_given_extra_folder_when_match_then_nested_file() -> None:
	assert path_matches_extra_sources(
		"WhatsApp/Media/a.jpg",
		frozenset({"WhatsApp/Media"}),
	)
	assert path_matches_extra_sources("notes.txt", frozenset({"notes.txt"}))
	assert not path_matches_extra_sources("other/a.jpg", frozenset({"WhatsApp/Media"}))


def test_given_duplicate_extras_when_merge_then_unique() -> None:
	assert merge_extra_paths(["Docs"], ["docs", "note.txt"]) == ["Docs", "note.txt"]
