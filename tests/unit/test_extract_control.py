from spacemaker.domain.extract_control import ExtractJobControl


def test_given_stop_requested_when_before_next_file_then_aborts_queue():
	# given
	control = ExtractJobControl()
	control.request_stop()
	# when / then
	assert control.before_next_file() is False


def test_given_pause_requested_when_after_file_then_marked_paused():
	# given
	control = ExtractJobControl()
	control.request_pause()
	# when
	control.after_file()
	# then
	assert control.is_paused()
