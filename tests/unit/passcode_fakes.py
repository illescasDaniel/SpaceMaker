from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.domain.network_passcode import PasscodeRecord, PasscodeStoreCorruptError


@dataclass
class FakePasscodeStore:
	record: PasscodeRecord | None = None
	corrupt: bool = False
	saves: int = 0

	def load(self) -> PasscodeRecord | None:
		if self.corrupt:
			raise PasscodeStoreCorruptError("unreadable")
		return self.record

	def save(self, record: PasscodeRecord) -> None:
		self.record = record
		self.corrupt = False
		self.saves += 1

	def clear(self) -> None:
		self.record = None
		self.corrupt = False


@dataclass
class FakePasscodeCrypto:
	"""Fast deterministic stand-in for scrypt + secrets; every random_bytes call differs."""

	_counter: int = 0

	def hash_passcode(self, passcode: str, salt: bytes) -> bytes:
		return hashlib.sha256(salt + passcode.encode("utf-8")).digest()

	def random_bytes(self, count: int) -> bytes:
		self._counter += 1
		return hashlib.sha256(str(self._counter).encode()).digest()[:count].ljust(count, b"\0")


@dataclass
class FakeClock:
	now: float = 1000.0
	ticks: list[float] = field(default_factory=list)

	def monotonic(self) -> float:
		return self.now

	def advance(self, seconds: float) -> None:
		self.now += seconds


def make_passcode(
	store: FakePasscodeStore | None = None,
	clock: FakeClock | None = None,
) -> tuple[NetworkPasscode, FakePasscodeStore, FakeClock]:
	store = store or FakePasscodeStore()
	clock = clock or FakeClock()
	use_case = NetworkPasscode(store, FakePasscodeCrypto(), clock)
	use_case.load()
	return use_case, store, clock
