from __future__ import annotations

import json
from pathlib import Path

import pytest

from spacemaker.adapters.outbound.preferences.passcode_store import JsonPasscodeStore
from spacemaker.adapters.outbound.security.scrypt_crypto import ScryptPasscodeCrypto
from spacemaker.domain.network_passcode import PasscodeRecord, PasscodeStoreCorruptError


def test_given_record_when_saved_then_load_round_trips_and_plaintext_absent(tmp_path: Path) -> None:
	# given
	path = tmp_path / "network_passcode.json"
	store = JsonPasscodeStore(path)
	record = PasscodeRecord(salt=b"s" * 16, passcode_hash=b"h" * 32, token_secret=b"t" * 32)
	# when
	store.save(record)
	# then
	assert store.load() == record
	assert "hunter2" not in path.read_text(encoding="utf-8")


def test_given_no_file_when_load_then_none(tmp_path: Path) -> None:
	# given
	store = JsonPasscodeStore(tmp_path / "missing.json")
	# when
	record = store.load()
	# then
	assert record is None


@pytest.mark.parametrize("content", ["not json", "[]", json.dumps({"salt": "!!!", "hash": "x", "secret": "y"}), "{}"])
def test_given_unreadable_file_when_load_then_corrupt_error(tmp_path: Path, content: str) -> None:
	# given
	path = tmp_path / "network_passcode.json"
	path.write_text(content, encoding="utf-8")
	# when / then
	with pytest.raises(PasscodeStoreCorruptError):
		JsonPasscodeStore(path).load()


def test_given_saved_when_clear_then_file_removed(tmp_path: Path) -> None:
	# given
	path = tmp_path / "network_passcode.json"
	store = JsonPasscodeStore(path)
	store.save(PasscodeRecord(salt=b"s" * 16, passcode_hash=b"h" * 32, token_secret=b"t" * 32))
	# when
	store.clear()
	# then
	assert not path.exists()
	assert store.load() is None


def test_given_same_inputs_when_scrypt_hashed_then_deterministic_and_salt_sensitive() -> None:
	# given
	crypto = ScryptPasscodeCrypto()
	# when
	first = crypto.hash_passcode("hunter2", b"a" * 16)
	again = crypto.hash_passcode("hunter2", b"a" * 16)
	other = crypto.hash_passcode("hunter2", b"b" * 16)
	# then
	assert first == again
	assert first != other
	assert len(first) == 32
	assert crypto.random_bytes(16) != crypto.random_bytes(16)
