from datetime import datetime

from tests.unit.fakes import FakeGalleryIndex

from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.domain.gallery import group_timeline
from spacemaker.domain.gallery_index import GalleryIndexRow
from spacemaker.domain.media import MediaKind


def test_given_items_in_two_years_when_group_timeline_then_orders_newest_first():
	# given
	from spacemaker.domain.gallery import gallery_item

	items = [
		gallery_item("a.avif", datetime(2024, 1, 1)),
		gallery_item("b.avif", datetime(2025, 3, 1)),
	]
	# when
	groups = group_timeline(items)
	# then
	assert groups[0].year == 2025
	assert groups[1].year == 2024


def test_given_indexed_items_when_list_timeline_page_then_returns_first_page():
	# given
	library = "/lib"
	index = FakeGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path="a.avif", captured_at=datetime(2025, 3, 1), kind=MediaKind.IMAGE, mtime=1, size=1
		),
		GalleryIndexRow(
			relative_path="b.avif", captured_at=datetime(2025, 3, 2), kind=MediaKind.IMAGE, mtime=1, size=1
		),
	]
	index.apply_sync(library, upserts=rows, removed=[])
	# when
	page = GenerateGallery(index).list_timeline_page(library, cursor=None, limit=10)
	# then
	assert [item.relative_path for item in page.items] == ["b.avif", "a.avif"]
	assert page.next_cursor is None


def test_given_more_items_than_limit_when_list_timeline_page_then_paginates():
	# given
	library = "/lib"
	index = FakeGalleryIndex()
	rows = [
		GalleryIndexRow(
			relative_path=f"{i}.avif", captured_at=datetime(2025, 3, i + 1), kind=MediaKind.IMAGE, mtime=1, size=1
		)
		for i in range(3)
	]
	index.apply_sync(library, upserts=rows, removed=[])
	gallery = GenerateGallery(index)
	# when
	first_page = gallery.list_timeline_page(library, cursor=None, limit=2)
	second_page = gallery.list_timeline_page(library, cursor=first_page.next_cursor, limit=2)
	# then
	assert [item.relative_path for item in first_page.items] == ["2.avif", "1.avif"]
	assert [item.relative_path for item in second_page.items] == ["0.avif"]
	assert second_page.next_cursor is None


def test_given_video_filename_when_gallery_item_then_kind_video():
	# given
	from spacemaker.domain.gallery import gallery_item

	# when
	item = gallery_item("clip.av1.mp4", datetime(2025, 1, 1))
	# then
	assert item.kind is MediaKind.VIDEO
