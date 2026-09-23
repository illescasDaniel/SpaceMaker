from tests.unit.fakes import FakeFileSystem, FakeMediaConverter, FakeMediaProbe

from spacemaker.application.convert_media import ConvertMedia
from spacemaker.domain.extract_control import ExtractJobControl
from spacemaker.domain.library import LibraryFolder


def test_given_stop_after_first_file_when_convert_then_stops_early():
	fs = FakeFileSystem()
	library = "/lib"
	fs.ensure_library_folders(library)
	fs.files[f"{library}/{LibraryFolder.ORIGINALS.value}/a.jpg"] = 100
	fs.files[f"{library}/{LibraryFolder.ORIGINALS.value}/b.jpg"] = 100
	control = ExtractJobControl()
	control.request_stop()
	use_case = ConvertMedia(fs, FakeMediaConverter(), FakeMediaProbe())
	progress = use_case.run(library, control=control)
	assert progress.total == 2
	assert progress.completed == 0
