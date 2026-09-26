from __future__ import annotations

from enum import StrEnum


class TransferFolder(StrEnum):
	"""Device folder labels for USB file transfer (any file types)."""

	DOWNLOAD = "download"
	DOCUMENTS = "documents"
	DCIM = "dcim"
	PICTURES = "pictures"
	MOVIES = "movies"
	MUSIC = "music"


ALL_TRANSFER_FOLDERS: frozenset[TransferFolder] = frozenset(TransferFolder)

DEFAULT_ANDROID_TRANSFER_FOLDERS: frozenset[TransferFolder] = frozenset(
	{TransferFolder.DOWNLOAD, TransferFolder.DOCUMENTS},
)

DEFAULT_IPHONE_TRANSFER_FOLDERS: frozenset[TransferFolder] = frozenset({TransferFolder.DCIM})

_FOLDER_PATH_MARKERS: dict[TransferFolder, frozenset[str]] = {
	TransferFolder.DOWNLOAD: frozenset({"download", "downloads"}),
	TransferFolder.DOCUMENTS: frozenset({"documents", "docs"}),
	TransferFolder.DCIM: frozenset({"dcim"}),
	TransferFolder.PICTURES: frozenset({"pictures"}),
	TransferFolder.MOVIES: frozenset({"movies"}),
	TransferFolder.MUSIC: frozenset({"music"}),
}


def parse_transfer_folders(values: list[str]) -> frozenset[TransferFolder]:
	out: set[TransferFolder] = set()
	for raw in values:
		try:
			out.add(TransferFolder(raw.lower()))
		except ValueError:
			continue
	return frozenset(out)


def path_matches_transfer_folders(device_path: str, selected: frozenset[TransferFolder]) -> bool:
	if not selected:
		return False
	normalized = device_path.lstrip("/").lower().replace("\\", "/")
	parts = frozenset(normalized.split("/"))
	for folder in selected:
		markers = _FOLDER_PATH_MARKERS[folder]
		if parts & markers:
			return True
	return False
