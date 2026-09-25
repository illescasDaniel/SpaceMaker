from datetime import datetime

from tests.unit.fakes import FakeGalleryIndex

from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.domain.gallery import days_in_month, gallery_item, items_for_day
from spacemaker.domain.gallery_index import GalleryIndexRow
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


def test_given_indexed_items_when_calendar_days_then_matches_index():
	# given
	library = "/lib"
	index = FakeGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path="a.avif", captured_at=datetime(2025, 3, 7), kind=MediaKind.IMAGE, mtime=1, size=1
		),
		GalleryIndexRow(
			relative_path="b.avif", captured_at=datetime(2025, 4, 1), kind=MediaKind.IMAGE, mtime=1, size=1
		),
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	days = GenerateGallery(index).calendar_days(library, 2025, 3)
	# then
	assert days == [7]


def test_given_indexed_items_when_list_day_then_matches_index():
	# given
	library = "/lib"
	index = FakeGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path="a.avif", captured_at=datetime(2025, 3, 7, 9), kind=MediaKind.IMAGE, mtime=1, size=1
		),
		GalleryIndexRow(
			relative_path="b.avif", captured_at=datetime(2025, 3, 8, 9), kind=MediaKind.IMAGE, mtime=1, size=1
		),
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	items = GenerateGallery(index).list_day(library, 2025, 3, 7)
	# then
	assert [item.relative_path for item in items] == ["a.avif"]
