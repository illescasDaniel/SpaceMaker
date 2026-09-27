from spacemaker.domain.transfer_folders import (
	DEFAULT_ANDROID_TRANSFER_FOLDERS,
	DEFAULT_IPHONE_TRANSFER_FOLDERS,
	TransferFolder,
	normalize_device_relative_path,
	parse_transfer_folders,
	path_matches_extra_sources,
	path_matches_transfer_folders,
	strip_android_user_storage_prefix,
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


def test_given_android_catalog_when_named_then_download_and_documents() -> None:
	assert TransferFolder.DOWNLOAD in DEFAULT_ANDROID_TRANSFER_FOLDERS
	assert TransferFolder.DOCUMENTS in DEFAULT_ANDROID_TRANSFER_FOLDERS
	assert TransferFolder.DCIM not in DEFAULT_ANDROID_TRANSFER_FOLDERS


def test_given_iphone_catalog_when_named_then_dcim_only() -> None:
	assert DEFAULT_IPHONE_TRANSFER_FOLDERS == frozenset({TransferFolder.DCIM})


def test_given_mount_relative_extra_when_absolute_path_then_matches() -> None:
	extras = frozenset({"WhatsApp/Media"})
	assert path_matches_extra_sources("/sdcard/WhatsApp/Media/a.jpg", extras)
	assert path_matches_extra_sources("/storage/emulated/0/WhatsApp/Media/x.bin", extras)
	assert not path_matches_extra_sources("/sdcard/WhatsApp/MediaBackup/a.jpg", extras)
	assert not path_matches_extra_sources("/sdcard/Download/a.pdf", extras)


def test_given_android_roots_when_strip_then_user_relative() -> None:
	# given / when / then
	assert strip_android_user_storage_prefix("/storage/self/primary/Download/a.pdf") == "Download/a.pdf"
	assert strip_android_user_storage_prefix("/storage/emulated/0/DCIM/b.jpg") == "DCIM/b.jpg"
	assert strip_android_user_storage_prefix("/sdcard/WhatsApp/Media/c.opus") == "WhatsApp/Media/c.opus"
	assert strip_android_user_storage_prefix("Download/a.pdf") == "Download/a.pdf"
	assert strip_android_user_storage_prefix("storage/self/primary") == ""


def test_given_prefixed_extra_when_normalize_then_flattened() -> None:
	assert normalize_device_relative_path("storage/self/primary/WhatsApp/Media") == "WhatsApp/Media"
	assert normalize_device_relative_path("/sdcard/notes.txt") == "notes.txt"
	assert normalize_device_relative_path("sdcard") is None
