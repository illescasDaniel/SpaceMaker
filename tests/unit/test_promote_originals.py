from pathlib import Path

from tests.unit.fakes import FakeFileSystem

from spacemaker.application.promote_originals import PromoteOriginalsToProcessed
from spacemaker.domain.library import LibraryFolder


def test_given_files_in_originals_when_promote_then_moved_to_processed():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	fs.files[f"{library}/{LibraryFolder.ORIGINALS.value}/a.jpg"] = 10
	fs.files[f"{library}/{LibraryFolder.ORIGINALS.value}/nested/b.png"] = 20
	# when
	progress = PromoteOriginalsToProcessed(fs).run(library)
	# then
	assert progress.completed == 2
	assert progress.total == 2
	assert f"{library}/{LibraryFolder.ORIGINALS.value}/a.jpg" not in fs.files
	assert fs.files[f"{library}/{LibraryFolder.PROCESSED.value}/a.jpg"] == 10
	assert fs.files[f"{library}/{LibraryFolder.PROCESSED.value}/nested/b.png"] == 20


def test_given_empty_originals_when_promote_then_noop():
	# given
	fs = FakeFileSystem()
	# when
	progress = PromoteOriginalsToProcessed(fs).run("/lib")
	# then
	assert progress.completed == 0
	assert progress.total == 0
