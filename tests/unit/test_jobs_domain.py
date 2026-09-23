from spacemaker.domain.jobs import (
	JobPhase,
	can_start_convert,
	convert_control_flags,
	extract_control_flags,
)


def test_given_originals_when_can_start_convert_then_true():
	assert can_start_convert(originals_count=5)


def test_given_no_originals_when_can_start_convert_then_false():
	assert not can_start_convert(originals_count=0)


def test_given_convert_running_when_can_start_convert_then_false():
	assert not can_start_convert(originals_count=5, convert_job_active=True)


def test_given_convert_running_when_convert_control_flags_then_stop_enabled():
	flags = convert_control_flags(JobPhase.RUNNING)
	assert flags["stop"] is True
	assert flags["start"] is False


def test_given_idle_when_extract_control_flags_then_start_enabled():
	flags = extract_control_flags(JobPhase.IDLE)
	assert flags["start"] is True
