from datetime import datetime

from tests.unit.fakes import FakeGalleryIndex

from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.domain.gallery_index import GalleryIndexRow
from spacemaker.domain.media import MediaKind


def _seed(library: str) -> FakeGalleryIndex:
	index = FakeGalleryIndex()
	rows = [
		GalleryIndexRow(relative_path=name, captured_at=datetime(2025, 9, day), kind=MediaKind.IMAGE, mtime=1, size=1)
		for day, name in ((4, "a.avif"), (5, "b.avif"), (6, "c.avif"))
	]
	index.apply_sync(library, upserts=rows, removed=[])
	return index


def test_given_middle_item_when_neighbor_next_then_returns_older_item():
	# given
	library = "/lib"
	gallery = GenerateGallery(_seed(library))
	# when
	found = gallery.neighbor(library, "b.avif", direction="next")
	# then
	assert found is not None
	assert found.relative_path == "a.avif"


def test_given_middle_item_when_neighbor_prev_then_returns_newer_item():
	# given
	library = "/lib"
	gallery = GenerateGallery(_seed(library))
	# when
	found = gallery.neighbor(library, "b.avif", direction="prev")
	# then
	assert found is not None
	assert found.relative_path == "c.avif"


def test_given_newest_item_when_neighbor_prev_then_none():
	# given
	library = "/lib"
	gallery = GenerateGallery(_seed(library))
	# when
	found = gallery.neighbor(library, "c.avif", direction="prev")
	# then
	assert found is None


def test_given_oldest_item_when_neighbor_next_then_none():
	# given
	library = "/lib"
	gallery = GenerateGallery(_seed(library))
	# when
	found = gallery.neighbor(library, "a.avif", direction="next")
	# then
	assert found is None
