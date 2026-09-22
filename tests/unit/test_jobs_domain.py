from spacemaker.domain.jobs import JobPhase, can_start_convert, extract_control_flags


def test_given_extract_running_when_can_start_convert_then_false():
	assert not can_start_convert(extract_phase=JobPhase.RUNNING, originals_count=5)


def test_given_idle_with_originals_when_can_start_convert_then_true():
	assert can_start_convert(extract_phase=JobPhase.IDLE, originals_count=2)


def test_given_stopped_with_originals_when_can_start_convert_then_true():
	assert can_start_convert(extract_phase=JobPhase.STOPPED, originals_count=2)


def test_given_running_when_extract_controls_then_pause_enabled():
	flags = extract_control_flags(JobPhase.RUNNING)
	assert flags["pause"] is True
	assert flags["start"] is False
