from __future__ import annotations

import base64
import binascii
import json
import os
import threading
from pathlib import Path

from spacemaker.domain.network_passcode import PasscodeRecord, PasscodeStoreCorruptError


class JsonPasscodeStore:
	"""Passcode record (salted hash + token secret) in its own file, owner-readable only."""

	def __init__(self, path: Path) -> None:
		self._path = path
		self._lock = threading.Lock()

	def load(self) -> PasscodeRecord | None:
		with self._lock:
			if not self._path.is_file():
				return None
			try:
				raw = json.loads(self._path.read_text(encoding="utf-8"))
				if not isinstance(raw, dict):
					raise PasscodeStoreCorruptError("not an object")
				return PasscodeRecord(
					salt=_decode(raw["salt"]),
					passcode_hash=_decode(raw["hash"]),
					token_secret=_decode(raw["secret"]),
				)
			except (OSError, ValueError, KeyError, TypeError, binascii.Error) as exc:
				raise PasscodeStoreCorruptError(str(exc)) from exc

	def save(self, record: PasscodeRecord) -> None:
		payload = {
			"salt": _encode(record.salt),
			"hash": _encode(record.passcode_hash),
			"secret": _encode(record.token_secret),
		}
		with self._lock:
			self._path.parent.mkdir(parents=True, exist_ok=True)
			tmp = self._path.with_suffix(self._path.suffix + ".tmp")
			fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
			with os.fdopen(fd, "w", encoding="utf-8") as handle:
				handle.write(json.dumps(payload, indent="\t", sort_keys=True) + "\n")
			tmp.replace(self._path)

	def clear(self) -> None:
		with self._lock:
			self._path.unlink(missing_ok=True)
			self._path.with_suffix(self._path.suffix + ".tmp").unlink(missing_ok=True)


def _encode(value: bytes) -> str:
	return base64.b64encode(value).decode("ascii")


def _decode(value: object) -> bytes:
	if not isinstance(value, str) or not value:
		raise ValueError("expected non-empty base64 string")
	return base64.b64decode(value.encode("ascii"), validate=True)
