from datetime import datetime

from tests.unit.fakes import FakeFileSystem

from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.domain.gallery import days_in_month, gallery_item, items_for_day
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.media import MediaKind


def test_given_items_on_two_days_when_days_in_month_then_lists_both():
	# given
	items = [
		gallery_item("a.avif", datetime(2025, 9, 2)),
		gallery_item("b.avif", datetime(2025, 9, 4)),
	]
	# when
	days = days_in_month(items, 2025, 9)
	# then
	assert days == frozenset({2, 4})


def test_given_day_filter_when_items_for_day_then_only_that_day():
	# given
	items = [
		gallery_item("a.avif", datetime(2025, 9, 4, 10, 0)),
		gallery_item("b.avif", datetime(2025, 9, 5, 10, 0)),
	]
	# when
	day_items = items_for_day(items, 2025, 9, 4)
	# then
	assert len(day_items) == 1
	assert day_items[0].relative_path == "a.avif"


def test_given_video_filename_when_gallery_item_then_kind_video():
	# given
	# when
	item = gallery_item("clip.av1.mp4", datetime(2025, 1, 1))
	# then
	assert item.kind is MediaKind.VIDEO


def test_given_converted_and_originals_when_calendar_days_then_converted_only():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	fs.files[f"{library}/{LibraryFolder.CONVERTED.value}/a.avif"] = 1
	fs.files[f"{library}/{LibraryFolder.ORIGINALS.value}/b.jpg"] = 1
	at = {"a.avif": datetime(2025, 3, 7)}
	# when
	days = GenerateGallery(fs).calendar_days(library, 2025, 3, captured_at_for=at)
	# then
	assert days == [7]
