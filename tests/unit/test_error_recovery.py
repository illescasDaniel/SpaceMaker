from tests.unit.fakes import FakeFileSystem

from spacemaker.application.error_recovery import ErrorRecovery
from spacemaker.domain.library import LibraryFolder


def test_given_error_files_when_move_all_to_converted_then_empties_error():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	fs.files[f"{library}/{LibraryFolder.ERROR.value}/a.jpg"] = 10
	# when
	moved = ErrorRecovery(fs).move_all_errors_to_converted(library)
	# then
	assert moved == 1
	assert fs.files[f"{library}/{LibraryFolder.CONVERTED.value}/a.jpg"] == 10
