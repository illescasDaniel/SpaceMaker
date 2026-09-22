from tests.unit.fakes import FakeFileSystem

from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.wizard import FolderWarnings, convert_step_state


def test_given_extract_complete_when_convert_step_then_can_start():
	# given
	# when
	state = convert_step_state(
		extract_complete=True,
		convert_running=False,
		convert_complete=False,
		progress_percent=0,
	)
	# then
	assert state.can_start is True


def test_given_error_files_when_count_then_warning_visible():
	# given
	fs = FakeFileSystem()
	fs.files["/lib/error/x.png"] = 1
	# when
	count = fs.count_files_in_folder("/lib", LibraryFolder.ERROR)
	warnings = FolderWarnings(error_count=count, invalid_count=0)
	# then
	assert warnings.has_error_warning is True
