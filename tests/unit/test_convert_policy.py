from spacemaker.domain.convert_policy import (
	ConvertStartPolicy,
	convert_start_policy,
	should_auto_drain_after_upload,
	should_requeue_convert_drain,
)
from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.ui_mode import UiMode


def test_given_easy_mode_when_convert_start_policy_then_concurrent():
	assert convert_start_policy(ui_mode=UiMode.EASY) is ConvertStartPolicy.CONCURRENT_WITH_EXTRACT


def test_given_advanced_mode_when_convert_start_policy_then_stop_extract():
	assert convert_start_policy(ui_mode=UiMode.ADVANCED) is ConvertStartPolicy.STOP_EXTRACT_FIRST


def test_given_easy_and_originals_when_should_auto_drain_then_true():
	assert should_auto_drain_after_upload(
		ui_mode=UiMode.EASY,
		convert_phase=JobPhase.IDLE,
		originals_count=2,
	)


def test_given_running_convert_when_should_auto_drain_then_false():
	assert not should_auto_drain_after_upload(
		ui_mode=UiMode.EASY,
		convert_phase=JobPhase.RUNNING,
		originals_count=2,
	)


def test_given_concurrent_and_remaining_when_should_requeue_then_true():
	assert should_requeue_convert_drain(concurrent_with_extract=True, remaining_originals=1)
