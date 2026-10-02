"""Network passcode value objects and lockout policy.

Spec: specs/network-passcode/SPEC.md. Access control only (no encryption);
hashing and storage live behind outbound ports.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


MIN_PASSCODE_LENGTH = 4
MAX_FAILED_ATTEMPTS = 5
BASE_LOCKOUT_SECONDS = 30
MAX_LOCKOUT_SECONDS = 900
MAX_TRACKED_CLIENTS = 1000
TOKEN_SECRET_BYTES = 32
SALT_BYTES = 16


class PasscodeTooShortError(ValueError):
	"""Passcode shorter than MIN_PASSCODE_LENGTH."""


class PasscodeStoreCorruptError(Exception):
	"""Stored hash/secret is unreadable; caller clears it and warns the user."""


@dataclass(frozen=True)
class PasscodeRecord:
	"""What is persisted: salted hash and the secret that derives logins. Never the plaintext."""

	salt: bytes
	passcode_hash: bytes
	token_secret: bytes


class UnlockOutcome(Enum):
	GRANTED = "granted"
	WRONG = "wrong"
	LOCKED_OUT = "locked_out"


@dataclass(frozen=True)
class UnlockResult:
	outcome: UnlockOutcome
	# Set when GRANTED: the value for the login cookie.
	login: str | None = None
	# Set when LOCKED_OUT: whole seconds until the next attempt is evaluated.
	retry_after_seconds: int = 0


def lockout_seconds(lockout_count: int) -> int:
	"""Duration of the Nth lockout (1-based): 30 s, doubling, capped at 15 min."""
	if lockout_count < 1:
		return 0
	return min(BASE_LOCKOUT_SECONDS * 2 ** (lockout_count - 1), MAX_LOCKOUT_SECONDS)
