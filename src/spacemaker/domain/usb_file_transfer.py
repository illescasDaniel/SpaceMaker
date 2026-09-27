from __future__ import annotations

from pathlib import Path

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase, extract_control_flags
from spacemaker.domain.transfer_folders import TransferFolder, strip_android_user_storage_prefix
from spacemaker.domain.upload_paths import normalize_upload_relative_path


USB_FILE_TRANSFER_METHODS: frozenset[ConnectionMethod] = frozenset(
	{
		ConnectionMethod.ADB,
		ConnectionMethod.AFC,
	},
)


def is_usb_file_transfer_method(method: ConnectionMethod) -> bool:
	return method in USB_FILE_TRANSFER_METHODS


def shows_iphone_limit_banner(method: ConnectionMethod) -> bool:
	"""Wireframe/spec: banner only when iPhone USB (AFC) is selected."""
	return method is ConnectionMethod.AFC


def default_transfer_folders(method: ConnectionMethod) -> frozenset[TransferFolder]:
	"""No presets are pre-checked; user opts in (or uses Browse extras)."""
	_ = method
	return frozenset()


def transfer_control_flags(transfer_phase: JobPhase) -> dict[str, bool]:
	"""Same Start/Pause/Resume/Stop enablement table as USB extract."""
	return extract_control_flags(transfer_phase)


def can_start_usb_file_transfer(
	*,
	has_device: bool,
	folders_selected: bool,
	phase: JobPhase,
	extras_selected: bool = False,
) -> bool:
	if not has_device or not (folders_selected or extras_selected):
		return False
	return transfer_control_flags(phase)["start"]


def documents_transfer_destination(dest_root: str, device_path: str) -> str | None:
	"""Map a device path to a safe path under the Documents/SpaceMaker root.

	Android user-storage prefixes (``sdcard``, ``storage/emulated/0``,
	``storage/self/primary``) are stripped so files land as ``Download/…``
	rather than nested under those mount aliases.
	"""
	flattened = strip_android_user_storage_prefix(device_path)
	relative = normalize_upload_relative_path(flattened)
	if relative is None:
		return None
	return str(Path(dest_root) / Path(relative))
