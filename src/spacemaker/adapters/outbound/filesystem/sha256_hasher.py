from __future__ import annotations

import hashlib
from pathlib import Path


class Sha256ContentHasher:
	def sha256_file(self, path: str) -> str:
		digest = hashlib.sha256()
		with Path(path).open("rb") as handle:
			while True:
				chunk = handle.read(1024 * 1024)
				if not chunk:
					break
				digest.update(chunk)
		return digest.hexdigest()
