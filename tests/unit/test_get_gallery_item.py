from datetime import datetime
from pathlib import Path

from tests.unit.fakes import FakeMediaProbe

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.get_gallery_item import GetGalleryItem
from spacemaker.domain.library import LibraryFolder


def test_given_converted_file_when_get_item_then_returns_detail(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	path = fs.library_path(library, LibraryFolder.CONVERTED, "photo.avif")
	Path(path).write_bytes(b"x")
	when = datetime(2025, 9, 4, 12, 0, 0)
	use_case = GetGalleryItem(fs, FakeMediaProbe())
	# when
	detail = use_case.get(library, "photo.avif", captured_at=when)
	# then
	assert detail is not None
	assert detail.item.relative_path == "photo.avif"
	assert detail.item.captured_at == when
	assert detail.metadata.filename == "photo.avif"


def test_given_missing_file_when_get_item_then_none(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	use_case = GetGalleryItem(fs, FakeMediaProbe())
	# when
	detail = use_case.get(library, "missing.avif")
	# then
	assert detail is None
