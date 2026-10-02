from __future__ import annotations

from typing import Protocol


class PasscodeCryptoPort(Protocol):
	"""Slow hash + randomness, so tests can substitute fast deterministic doubles."""

	def hash_passcode(self, passcode: str, salt: bytes) -> bytes:
		"""Salted scrypt in production (~100 ms; callers run it off the event loop)."""
		...

	def random_bytes(self, count: int) -> bytes: ...
