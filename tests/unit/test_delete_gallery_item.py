from pathlib import Path

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.delete_gallery_item import DeleteGalleryItem
from spacemaker.domain.gallery_cache_paths import export_cache_path, thumbnail_path
from spacemaker.domain.gallery_export import ExportFormat
from spacemaker.domain.library import LibraryFolder


def test_given_converted_file_when_delete_then_removed_and_caches_cleared(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	rel = "2025/photo.avif"
	converted = fs.library_path(library, LibraryFolder.CONVERTED, rel)
	Path(converted).parent.mkdir(parents=True, exist_ok=True)
	Path(converted).write_bytes(b"x")
	thumb = Path(thumbnail_path(library, rel))
	thumb.parent.mkdir(parents=True, exist_ok=True)
	thumb.write_bytes(b"thumb")
	export_jpeg = Path(export_cache_path(library, rel, ExportFormat.JPEG))
	export_jpeg.parent.mkdir(parents=True, exist_ok=True)
	export_jpeg.write_bytes(b"jpeg")
	use_case = DeleteGalleryItem(fs)
	# when
	removed = use_case.run(library, rel)
	# then
	assert removed is True
	assert not Path(converted).is_file()
	assert not thumb.is_file()
	assert not export_jpeg.is_file()


def test_given_missing_file_when_delete_then_false(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	use_case = DeleteGalleryItem(fs)
	# when
	removed = use_case.run(library, "missing.avif")
	# then
	assert removed is False
