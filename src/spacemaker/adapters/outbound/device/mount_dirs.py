from __future__ import annotations

import contextlib
from pathlib import Path


def remove_empty_mount_dir(path: Path) -> None:
	"""Remove a mount point directory only if it is empty.

	Never ``rmtree``: if the unmount failed, the directory is still the live FUSE view of the
	phone, and a recursive delete would erase the device's real files.
	"""
	with contextlib.suppress(OSError):
		path.rmdir()
