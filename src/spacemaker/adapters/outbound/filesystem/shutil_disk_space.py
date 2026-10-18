from __future__ import annotations

import shutil
from pathlib import Path


class ShutilDiskSpace:
	def free_bytes(self, path: str) -> int:
		target = Path(path)
		while not target.exists() and target != target.parent:
			target = target.parent
		return shutil.disk_usage(target).free
