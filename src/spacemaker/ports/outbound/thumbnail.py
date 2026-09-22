from __future__ import annotations

from typing import Protocol


class ThumbnailPort(Protocol):
	def ensure_thumb(self, library_root: str, relative_path: str) -> str: ...
