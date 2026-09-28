from spacemaker.domain.library import live_job_progress


def test_given_zero_completed_and_one_original_when_live_job_progress_then_0_of_1():
	# given / when
	progress = live_job_progress(0, 1)
	# then
	assert progress.completed == 0
	assert progress.total == 1
	assert progress.percent == 0


def test_given_one_completed_and_one_remaining_when_live_job_progress_then_1_of_2():
	# given / when
	progress = live_job_progress(1, 1)
	# then
	assert progress.completed == 1
	assert progress.total == 2
	assert progress.percent == 50


def test_given_all_done_when_live_job_progress_then_100_percent():
	# given / when
	progress = live_job_progress(3, 0)
	# then
	assert progress.completed == 3
	assert progress.total == 3
	assert progress.percent == 100


def test_given_empty_when_live_job_progress_then_0_of_0():
	# given / when
	progress = live_job_progress(0, 0)
	# then
	assert progress.completed == 0
	assert progress.total == 0
	assert progress.percent == 0


def test_given_negative_inputs_when_live_job_progress_then_clamped_non_negative():
	# given / when
	progress = live_job_progress(-2, -1)
	# then
	assert progress.completed == 0
	assert progress.total == 0
