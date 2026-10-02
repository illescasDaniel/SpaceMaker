from __future__ import annotations

import pytest
from tests.unit.passcode_fakes import FakePasscodeStore, make_passcode

from spacemaker.domain.network_passcode import (
	MAX_FAILED_ATTEMPTS,
	MAX_LOCKOUT_SECONDS,
	MAX_TRACKED_CLIENTS,
	PasscodeTooShortError,
	UnlockOutcome,
	lockout_seconds,
)


PHONE = "192.168.1.50"


def _fail_times(use_case, count: int, client: str = PHONE) -> None:  # type: ignore[no-untyped-def]
	for _ in range(count):
		use_case.unlock_with_passcode(client, "wrong")


def test_given_never_set_when_checked_then_disabled_and_every_login_valid() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	# when / then
	assert use_case.enabled is False
	assert use_case.qr_token() is None
	assert use_case.is_login_valid(None) is True


def test_given_passcode_set_when_checked_then_enabled_and_login_required() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	# when
	use_case.set_passcode("hunter2")
	# then
	assert use_case.enabled is True
	assert use_case.is_login_valid(None) is False
	assert use_case.is_login_valid("nonsense") is False


def test_given_too_short_passcode_when_set_then_error_and_nothing_stored() -> None:
	# given
	use_case, store, _clock = make_passcode()
	# when
	with pytest.raises(PasscodeTooShortError):
		use_case.set_passcode("abc")
	# then
	assert use_case.enabled is False
	assert store.record is None


def test_given_passcode_set_when_unlock_with_correct_passcode_then_login_is_valid() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	# when
	result = use_case.unlock_with_passcode(PHONE, "hunter2")
	# then
	assert result.outcome is UnlockOutcome.GRANTED
	assert result.login
	assert use_case.is_login_valid(result.login) is True


def test_given_passcode_set_when_unlock_with_qr_token_then_granted() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	token = use_case.qr_token()
	assert token
	# when
	result = use_case.unlock_with_token(PHONE, token)
	# then
	assert result.outcome is UnlockOutcome.GRANTED
	assert use_case.is_login_valid(result.login) is True


def test_given_wrong_passcode_when_unlock_then_wrong_and_no_login() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	# when
	result = use_case.unlock_with_passcode(PHONE, "nope")
	# then
	assert result.outcome is UnlockOutcome.WRONG
	assert result.login is None


def test_given_wrong_token_when_unlock_then_wrong() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	# when
	result = use_case.unlock_with_token(PHONE, "forged")
	# then
	assert result.outcome is UnlockOutcome.WRONG


def test_given_five_wrong_tries_when_unlock_within_30s_then_locked_out_without_evaluating() -> None:
	# given
	use_case, _store, clock = make_passcode()
	use_case.set_passcode("hunter2")
	_fail_times(use_case, MAX_FAILED_ATTEMPTS)
	clock.advance(10)
	# when (the correct passcode must not be evaluated while locked)
	result = use_case.unlock_with_passcode(PHONE, "hunter2")
	# then
	assert result.outcome is UnlockOutcome.LOCKED_OUT
	assert result.login is None
	assert result.retry_after_seconds == 20


def test_given_lockout_elapsed_when_unlock_then_correct_passcode_granted() -> None:
	# given
	use_case, _store, clock = make_passcode()
	use_case.set_passcode("hunter2")
	_fail_times(use_case, MAX_FAILED_ATTEMPTS)
	clock.advance(31)
	# when
	result = use_case.unlock_with_passcode(PHONE, "hunter2")
	# then
	assert result.outcome is UnlockOutcome.GRANTED


def test_given_second_lockout_when_failing_again_then_lasts_60_seconds() -> None:
	# given
	use_case, _store, clock = make_passcode()
	use_case.set_passcode("hunter2")
	_fail_times(use_case, MAX_FAILED_ATTEMPTS)
	clock.advance(31)
	_fail_times(use_case, MAX_FAILED_ATTEMPTS)
	# when
	result = use_case.unlock_with_passcode(PHONE, "hunter2")
	# then
	assert result.outcome is UnlockOutcome.LOCKED_OUT
	assert result.retry_after_seconds == 60


def test_given_other_client_when_one_is_locked_out_then_other_is_unaffected() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	_fail_times(use_case, MAX_FAILED_ATTEMPTS)
	# when
	result = use_case.unlock_with_passcode("192.168.1.99", "hunter2")
	# then
	assert result.outcome is UnlockOutcome.GRANTED


def test_given_many_clients_when_tracking_then_table_is_capped() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	# when
	for index in range(MAX_TRACKED_CLIENTS + 50):
		use_case.unlock_with_passcode(f"10.0.{index // 250}.{index % 250}", "wrong")
	# then
	assert use_case.tracked_client_count <= MAX_TRACKED_CLIENTS


def test_given_logged_in_phone_when_passcode_changed_then_old_login_and_qr_token_invalid() -> None:
	# given
	use_case, _store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	login = use_case.unlock_with_passcode(PHONE, "hunter2").login
	old_token = use_case.qr_token()
	assert old_token
	# when
	use_case.set_passcode("correct horse")
	# then
	assert use_case.is_login_valid(login) is False
	assert use_case.unlock_with_token(PHONE, old_token).outcome is UnlockOutcome.WRONG
	assert use_case.unlock_with_passcode(PHONE, "hunter2").outcome is UnlockOutcome.WRONG


def test_given_logged_in_phone_when_cleared_then_disabled_and_served_openly() -> None:
	# given
	use_case, store, _clock = make_passcode()
	use_case.set_passcode("hunter2")
	# when
	use_case.clear()
	# then
	assert use_case.enabled is False
	assert use_case.is_login_valid(None) is True
	assert store.record is None


def test_given_stored_record_when_restarted_then_enabled_and_login_survives() -> None:
	# given
	first, store, clock = make_passcode()
	first.set_passcode("hunter2")
	login = first.unlock_with_passcode(PHONE, "hunter2").login
	# when
	second, _store, _clock = make_passcode(store, clock)
	# then
	assert second.enabled is True
	assert second.is_login_valid(login) is True
	assert second.unlock_with_passcode(PHONE, "hunter2").outcome is UnlockOutcome.GRANTED


def test_given_corrupt_store_when_loaded_then_cleared_with_warning_and_open() -> None:
	# given
	store = FakePasscodeStore(corrupt=True)
	# when
	use_case, _store, _clock = make_passcode(store)
	# then
	assert use_case.enabled is False
	assert use_case.corrupt_warning is True
	assert store.corrupt is False
	assert use_case.is_login_valid(None) is True


def test_given_passcode_set_when_inspecting_stored_record_then_plaintext_absent() -> None:
	# given
	use_case, store, _clock = make_passcode()
	# when
	use_case.set_passcode("hunter2")
	# then
	assert store.record is not None
	blob = store.record.salt + store.record.passcode_hash + store.record.token_secret
	assert b"hunter2" not in blob


def test_given_lockout_counts_when_computing_duration_then_it_doubles_and_caps() -> None:
	# given
	counts = (0, 1, 2, 3)
	# when
	durations = [lockout_seconds(n) for n in counts]
	# then
	assert durations == [0, 30, 60, 120]
	assert lockout_seconds(50) == MAX_LOCKOUT_SECONDS
