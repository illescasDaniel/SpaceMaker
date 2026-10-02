from __future__ import annotations

import hashlib
import secrets


class ScryptPasscodeCrypto:
	"""stdlib scrypt (N=2^14, r=8, p=1: ~100 ms) and OS randomness."""

	def hash_passcode(self, passcode: str, salt: bytes) -> bytes:
		return hashlib.scrypt(passcode.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)

	def random_bytes(self, count: int) -> bytes:
		return secrets.token_bytes(count)
