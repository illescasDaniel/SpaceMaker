from spacemaker.domain.jobs import JobPhase
from spacemaker.domain.wizard import StepPhase, visualize_step_state


def test_given_converted_files_when_visualize_step_then_ready_count():
	# given
	# when
	state = visualize_step_state(
		converted_count=42,
		convert_phase=JobPhase.IDLE,
		progress_percent=0,
	)
	# then
	assert state.phase is StepPhase.COMPLETED
	assert "42" in state.status_text
	assert state.can_start is True


def test_given_empty_converted_when_visualize_step_then_not_started():
	# given
	# when
	state = visualize_step_state(
		converted_count=0,
		convert_phase=JobPhase.IDLE,
		progress_percent=0,
	)
	# then
	assert state.status_text == "Not started"
	assert state.can_start is False


def test_given_convert_running_when_visualize_step_then_in_progress():
	# given
	# when
	state = visualize_step_state(
		converted_count=0,
		convert_phase=JobPhase.RUNNING,
		progress_percent=55,
	)
	# then
	assert state.phase is StepPhase.IN_PROGRESS
	assert "55%" in state.status_text
	assert state.can_start is True
