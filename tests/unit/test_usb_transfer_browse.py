from spacemaker.domain.transfer_folders import (
	TransferFolder,
	existing_transfer_folders_from_dir_names,
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


def test_given_extra_folder_when_match_then_nested_file() -> None:
	assert path_matches_extra_sources(
		"WhatsApp/Media/a.jpg",
		frozenset({"WhatsApp/Media"}),
	)
	assert path_matches_extra_sources("notes.txt", frozenset({"notes.txt"}))
	assert not path_matches_extra_sources("other/a.jpg", frozenset({"WhatsApp/Media"}))


def test_given_duplicate_extras_when_merge_then_unique() -> None:
	assert merge_extra_paths(["Docs"], ["docs", "note.txt"]) == ["Docs", "note.txt"]
