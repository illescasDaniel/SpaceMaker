from __future__ import annotations

from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort
from spacemaker.ports.outbound.filesystem import FileSystemPort


class PullVerificationError(RuntimeError):
	"""A pulled file does not match the device copy, so the device original must be kept."""


def delete_device_file_after_verified_pull(
	devices: DeviceRepositoryPort,
	filesystem: FileSystemPort,
	device_id: str,
	device_path: str,
	dest: str,
) -> None:
	"""Move mode: remove the device file only once the local copy provably matches it.

	An unknown remote size (0) keeps the device file; a size mismatch drops the partial local
	copy and raises, so a truncated pull can never lead to device data loss.
	"""
	remote = devices.remote_file_size(device_id, device_path)
	if remote <= 0:
		return
	local = filesystem.file_size(dest) if filesystem.exists(dest) else -1
	if local != remote:
		if local >= 0:
			filesystem.delete_file(dest)
		raise PullVerificationError(
			f"{device_path}: copied {max(local, 0)} of {remote} bytes; device file kept (Move aborted)",
		)
	devices.delete_device_file(device_id, device_path)
