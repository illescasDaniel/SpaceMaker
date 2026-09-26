from __future__ import annotations

from pathlib import Path

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.jobs import JobPhase, extract_control_flags
from spacemaker.domain.transfer_folders import (
	DEFAULT_ANDROID_TRANSFER_FOLDERS,
	DEFAULT_IPHONE_TRANSFER_FOLDERS,
	TransferFolder,
)
from spacemaker.domain.upload_paths import normalize_upload_relative_path


USB_FILE_TRANSFER_METHODS: frozenset[ConnectionMethod] = frozenset(
	{
		ConnectionMethod.MTP,
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
	if method is ConnectionMethod.AFC:
		return DEFAULT_IPHONE_TRANSFER_FOLDERS
	return DEFAULT_ANDROID_TRANSFER_FOLDERS


def transfer_control_flags(transfer_phase: JobPhase) -> dict[str, bool]:
	"""Same Start/Pause/Resume/Stop enablement table as USB extract."""
	return extract_control_flags(transfer_phase)


def can_start_usb_file_transfer(
	*,
	has_device: bool,
	folders_selected: bool,
	phase: JobPhase,
) -> bool:
	if not has_device or not folders_selected:
		return False
	return transfer_control_flags(phase)["start"]


def documents_transfer_destination(dest_root: str, device_path: str) -> str | None:
	"""Map a device path to a safe path under the Documents/SpaceMaker root."""
	relative = normalize_upload_relative_path(device_path.lstrip("/"))
	if relative is None:
		return None
	return str(Path(dest_root) / Path(relative))
