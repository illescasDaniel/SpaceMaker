from __future__ import annotations

from typing import Protocol

from spacemaker.domain.network_passcode import PasscodeRecord


class PasscodeStorePort(Protocol):
	"""Durable storage for the passcode record, separate from user preferences
	so Clear preferences / Reset library never silently disables protection."""

	def load(self) -> PasscodeRecord | None:
		"""None when no passcode is set. Raises PasscodeStoreCorruptError when unreadable."""
		...

	def save(self, record: PasscodeRecord) -> None: ...

	def clear(self) -> None: ...
