from __future__ import annotations

from pathlib import Path

from spacemaker.domain.library_paths import SKIPPED_LIBRARY_DIR_NAMES
from spacemaker.domain.transfer_folders import (
	TransferFolder,
	existing_transfer_folders_from_dir_names,
	host_path_to_device_relative,
	merge_extra_paths,
)


def collect_mount_dir_names(mount_root: str | Path) -> frozenset[str]:
	"""Collect top-level directory basenames under a phone mount (preset exist-probe).

	Shallow only — full ``os.walk`` over FUSE (adbfs/ifuse) can hang on trash or
	permission-denied entries and freeze the UI thread.
	"""
	root = Path(mount_root)
	if not root.is_dir():
		return frozenset()
	names: set[str] = set()
	try:
		for entry in root.iterdir():
			name = entry.name
			if name in SKIPPED_LIBRARY_DIR_NAMES:
				continue
			try:
				if entry.is_dir():
					names.add(name)
			except OSError:
				continue
	except OSError:
		return frozenset()
	return frozenset(names)


def probe_existing_transfer_folders(mount_root: str | Path) -> frozenset[TransferFolder]:
	return existing_transfer_folders_from_dir_names(collect_mount_dir_names(mount_root))


def device_relative_paths_from_host_picks(mount_root: str, host_paths: list[str]) -> list[str]:
	"""Convert host picks under mount to device-relative paths; drop escapes."""
	accepted: list[str] = []
	for host in host_paths:
		relative = host_path_to_device_relative(mount_root, host)
		if relative is not None:
			accepted.append(relative)
	return merge_extra_paths([], accepted)
