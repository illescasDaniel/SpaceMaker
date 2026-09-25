from datetime import datetime

from tests.unit.fakes import FakeFileSystem, FakeGalleryIndex, FakeMediaProbe

from spacemaker.application.sync_gallery_index import SyncGalleryIndex
from spacemaker.domain.library import LibraryFolder


def _converted_path(library: str, relative: str) -> str:
	return f"{library}/{LibraryFolder.CONVERTED.value}/{relative}"


def test_given_new_file_on_disk_when_run_then_probed_and_added_to_index():
	# given
	library = "/lib"
	full = _converted_path(library, "a.avif")
	fs = FakeFileSystem()
	fs.files[full] = 10
	fs.mtimes[full] = 100.0
	probe = FakeMediaProbe(captured_at_map={full: datetime(2025, 9, 4)})
	index = FakeGalleryIndex()
	sync = SyncGalleryIndex(fs, probe, index)
	# when
	plan = sync.run(library)
	# then
	assert plan.added == ("a.avif",)
	row = index.get(library, "a.avif")
	assert row is not None
	assert row.captured_at == datetime(2025, 9, 4)


def test_given_unchanged_file_when_run_twice_then_second_run_does_not_reprobe():
	# given
	library = "/lib"
	full = _converted_path(library, "a.avif")
	fs = FakeFileSystem()
	fs.files[full] = 10
	fs.mtimes[full] = 100.0
	probe = FakeMediaProbe(captured_at_map={full: datetime(2025, 9, 4)})
	index = FakeGalleryIndex()
	sync = SyncGalleryIndex(fs, probe, index)
	sync.run(library)
	calls_after_first_run = len(probe.captured_at_calls)
	# when
	plan = sync.run(library)
	# then
	assert plan.is_empty
	assert len(probe.captured_at_calls) == calls_after_first_run


def test_given_one_changed_file_when_run_then_only_that_file_is_reprobed():
	# given
	library = "/lib"
	full_a = _converted_path(library, "a.avif")
	full_b = _converted_path(library, "b.avif")
	fs = FakeFileSystem()
	fs.files[full_a] = 10
	fs.mtimes[full_a] = 100.0
	fs.files[full_b] = 20
	fs.mtimes[full_b] = 200.0
	probe = FakeMediaProbe(captured_at_map={full_a: datetime(2025, 9, 4), full_b: datetime(2025, 9, 5)})
	index = FakeGalleryIndex()
	sync = SyncGalleryIndex(fs, probe, index)
	sync.run(library)
	probe.captured_at_calls.clear()
	fs.mtimes[full_b] = 201.0
	probe.captured_at_map[full_b] = datetime(2025, 9, 6)
	# when
	plan = sync.run(library)
	# then
	assert plan.changed == ("b.avif",)
	assert probe.captured_at_calls == [full_b]
	row_b = index.get(library, "b.avif")
	row_a = index.get(library, "a.avif")
	assert row_b is not None
	assert row_a is not None
	assert row_b.captured_at == datetime(2025, 9, 6)
	assert row_a.captured_at == datetime(2025, 9, 4)


def test_given_files_in_originals_and_converted_when_run_then_only_converted_indexed():
	# given
	library = "/lib"
	converted = _converted_path(library, "a.avif")
	original = f"{library}/{LibraryFolder.ORIGINALS.value}/b.jpg"
	fs = FakeFileSystem()
	fs.files[converted] = 10
	fs.mtimes[converted] = 100.0
	fs.files[original] = 10
	fs.mtimes[original] = 100.0
	probe = FakeMediaProbe(captured_at_map={converted: datetime(2025, 9, 4)})
	index = FakeGalleryIndex()
	sync = SyncGalleryIndex(fs, probe, index)
	# when
	sync.run(library)
	# then
	assert index.get(library, "a.avif") is not None
	assert index.count(library) == 1


def test_given_removed_file_when_run_then_dropped_from_index():
	# given
	library = "/lib"
	full = _converted_path(library, "a.avif")
	fs = FakeFileSystem()
	fs.files[full] = 10
	fs.mtimes[full] = 100.0
	probe = FakeMediaProbe(captured_at_map={full: datetime(2025, 9, 4)})
	index = FakeGalleryIndex()
	sync = SyncGalleryIndex(fs, probe, index)
	sync.run(library)
	del fs.files[full]
	del fs.mtimes[full]
	# when
	plan = sync.run(library)
	# then
	assert plan.removed == ("a.avif",)
	assert index.get(library, "a.avif") is None
