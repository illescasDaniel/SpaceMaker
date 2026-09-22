from datetime import datetime

from tests.unit.fakes import FakeFileSystem

from spacemaker.application.generate_gallery import GenerateGallery
from spacemaker.domain.gallery import group_timeline
from spacemaker.domain.library import LibraryFolder


def test_given_items_in_two_years_when_group_timeline_then_orders_newest_first():
	# given
	from spacemaker.domain.gallery import GalleryItem

	items = [
		GalleryItem("a", datetime(2024, 1, 1)),
		GalleryItem("b", datetime(2025, 3, 1)),
	]
	# when
	groups = group_timeline(items)
	# then
	assert groups[0].year == 2025
	assert groups[1].year == 2024


def test_given_converted_files_when_generate_then_lists_only_converted():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	fs.files[f"{library}/{LibraryFolder.CONVERTED.value}/a.avif"] = 1
	fs.files[f"{library}/{LibraryFolder.ORIGINALS.value}/b.jpg"] = 1
	# when
	groups = GenerateGallery(fs).list_timeline(library)
	# then
	assert len(groups) == 1
	assert groups[0].items[0].relative_path == "a.avif"
