"""Network passcode use case (spec: specs/network-passcode/SPEC.md).

Owns the cached record, login/QR-token derivation (HMAC of the stored secret)
and the in-memory per-client lockout table. Inbound adapters only call this.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from spacemaker.domain.network_passcode import (
	MAX_FAILED_ATTEMPTS,
	MAX_TRACKED_CLIENTS,
	MIN_PASSCODE_LENGTH,
	SALT_BYTES,
	TOKEN_SECRET_BYTES,
	PasscodeRecord,
	PasscodeStoreCorruptError,
	PasscodeTooShortError,
	UnlockOutcome,
	UnlockResult,
	lockout_seconds,
)
from spacemaker.ports.outbound.clock import ClockPort
from spacemaker.ports.outbound.passcode_crypto import PasscodeCryptoPort
from spacemaker.ports.outbound.passcode_store import PasscodeStorePort


_LOGIN_LABEL = b"login"
_QR_LABEL = b"qr"

_Matcher = Callable[[], bool]


@dataclass
class _ClientAttempts:
	failures: int = 0
	lockouts: int = 0
	locked_until: float = 0.0


class NetworkPasscode:
	def __init__(
		self,
		store: PasscodeStorePort,
		crypto: PasscodeCryptoPort,
		clock: ClockPort,
	) -> None:
		self._store = store
		self._crypto = crypto
		self._clock = clock
		self._lock = threading.Lock()
		self._record: PasscodeRecord | None = None
		self._corrupt_warning = False
		self._attempts: OrderedDict[str, _ClientAttempts] = OrderedDict()

	def load(self) -> None:
		"""Read the stored record at startup. Corrupt -> cleared; see `corrupt_warning`."""
		with self._lock:
			try:
				self._record = self._store.load()
			except PasscodeStoreCorruptError:
				self._store.clear()
				self._record = None
				self._corrupt_warning = True

	@property
	def corrupt_warning(self) -> bool:
		"""True after a corrupt store was cleared on load (Home shows a warning)."""
		return self._corrupt_warning

	@property
	def enabled(self) -> bool:
		return self._record is not None

	@property
	def tracked_client_count(self) -> int:
		with self._lock:
			return len(self._attempts)

	def set_passcode(self, passcode: str) -> None:
		"""Set or change. Raises PasscodeTooShortError. Rotates the token secret."""
		if len(passcode) < MIN_PASSCODE_LENGTH:
			raise PasscodeTooShortError(f"passcode must be at least {MIN_PASSCODE_LENGTH} characters")
		salt = self._crypto.random_bytes(SALT_BYTES)
		record = PasscodeRecord(
			salt=salt,
			passcode_hash=self._crypto.hash_passcode(passcode, salt),
			token_secret=self._crypto.random_bytes(TOKEN_SECRET_BYTES),
		)
		with self._lock:
			self._store.save(record)
			self._record = record
			self._attempts.clear()
			self._corrupt_warning = False

	def clear(self) -> None:
		"""Remove the passcode and discard the secret (signs everyone out)."""
		with self._lock:
			self._store.clear()
			self._record = None
			self._attempts.clear()
			self._corrupt_warning = False

	def qr_token(self) -> str | None:
		"""Token for the `#k=` fragment of phone URLs; None when disabled."""
		record = self._record
		if record is None:
			return None
		return _derive(record, _QR_LABEL)

	def unlock_with_passcode(self, client_id: str, passcode: str) -> UnlockResult:
		record = self._record
		if record is None:
			return UnlockResult(UnlockOutcome.GRANTED)
		return self._attempt(
			client_id,
			record,
			lambda: hmac.compare_digest(self._crypto.hash_passcode(passcode, record.salt), record.passcode_hash),
		)

	def unlock_with_token(self, client_id: str, token: str) -> UnlockResult:
		record = self._record
		if record is None:
			return UnlockResult(UnlockOutcome.GRANTED)
		return self._attempt(
			client_id,
			record,
			lambda: hmac.compare_digest(token.encode("utf-8"), _derive(record, _QR_LABEL).encode("utf-8")),
		)

	def is_login_valid(self, login: str | None) -> bool:
		"""Constant-time check of the cookie value; always True when disabled."""
		record = self._record
		if record is None:
			return True
		expected = _derive(record, _LOGIN_LABEL).encode("utf-8")
		return hmac.compare_digest((login or "").encode("utf-8"), expected)

	def _attempt(self, client_id: str, record: PasscodeRecord, matches: _Matcher) -> UnlockResult:
		now = self._clock.monotonic()
		with self._lock:
			state = self._attempts.get(client_id)
			if state is not None and state.locked_until > now:
				return UnlockResult(
					UnlockOutcome.LOCKED_OUT,
					retry_after_seconds=math.ceil(state.locked_until - now),
				)
		# Slow hash outside the lock so one client never stalls the others.
		ok = matches()
		with self._lock:
			if ok:
				self._attempts.pop(client_id, None)
				return UnlockResult(UnlockOutcome.GRANTED, login=_derive(record, _LOGIN_LABEL))
			state = self._attempts.setdefault(client_id, _ClientAttempts())
			self._attempts.move_to_end(client_id)
			state.failures += 1
			if state.failures >= MAX_FAILED_ATTEMPTS:
				state.failures = 0
				state.lockouts += 1
				state.locked_until = now + lockout_seconds(state.lockouts)
			while len(self._attempts) > MAX_TRACKED_CLIENTS:
				self._attempts.popitem(last=False)
			return UnlockResult(UnlockOutcome.WRONG)


def _derive(record: PasscodeRecord, label: bytes) -> str:
	return hmac.new(record.token_secret, label, hashlib.sha256).hexdigest()
