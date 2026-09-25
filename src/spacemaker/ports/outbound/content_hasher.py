from __future__ import annotations

from typing import Protocol


class ContentHasher(Protocol):
	"""Outbound port: content digest for transfer-session dedupe."""

	def sha256_file(self, path: str) -> str: ...
