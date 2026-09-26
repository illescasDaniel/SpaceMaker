from spacemaker.domain.transfer_folders import (
	DEFAULT_ANDROID_TRANSFER_FOLDERS,
	DEFAULT_IPHONE_TRANSFER_FOLDERS,
	TransferFolder,
	parse_transfer_folders,
	path_matches_transfer_folders,
)


def test_given_download_path_when_download_selected_then_matches() -> None:
	# given
	selected = frozenset({TransferFolder.DOWNLOAD})
	# when / then
	assert path_matches_transfer_folders("/sdcard/Download/report.pdf", selected)
	assert path_matches_transfer_folders("/storage/emulated/0/Download/a.txt", selected)


def test_given_documents_path_when_only_download_selected_then_no_match() -> None:
	# given
	selected = frozenset({TransferFolder.DOWNLOAD})
	# when / then
	assert not path_matches_transfer_folders("/sdcard/Documents/notes.txt", selected)


def test_given_empty_selection_when_match_then_false() -> None:
	assert not path_matches_transfer_folders("/sdcard/Download/a.pdf", frozenset())


def test_given_mixed_labels_when_parse_then_keeps_known() -> None:
	# given / when
	parsed = parse_transfer_folders(["download", "BOGUS", "Documents"])
	# then
	assert parsed == frozenset({TransferFolder.DOWNLOAD, TransferFolder.DOCUMENTS})


def test_given_defaults_when_android_then_download_and_documents() -> None:
	assert TransferFolder.DOWNLOAD in DEFAULT_ANDROID_TRANSFER_FOLDERS
	assert TransferFolder.DOCUMENTS in DEFAULT_ANDROID_TRANSFER_FOLDERS
	assert TransferFolder.DCIM not in DEFAULT_ANDROID_TRANSFER_FOLDERS


def test_given_defaults_when_iphone_then_dcim_only() -> None:
	assert DEFAULT_IPHONE_TRANSFER_FOLDERS == frozenset({TransferFolder.DCIM})
