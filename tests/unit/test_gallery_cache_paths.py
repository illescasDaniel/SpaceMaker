from pathlib import Path

from spacemaker.domain.gallery_cache_paths import (
	export_cache_path,
	export_cache_paths_for_relative,
	is_legacy_hash_export_filename,
	thumbnail_path,
)
from spacemaker.domain.gallery_export import ExportFormat


def test_given_distinct_stems_when_thumbnail_path_then_injective() -> None:
	# given
	library = "/lib"
	# when
	avif_thumb = thumbnail_path(library, "2025/vacation.avif")
	mp4_thumb = thumbnail_path(library, "2025/vacation.mp4")
	# then
	assert avif_thumb != mp4_thumb
	assert avif_thumb.endswith("/.thumbnails/2025/vacation.avif.jpg")
	assert mp4_thumb.endswith("/.thumbnails/2025/vacation.mp4.jpg")


def test_given_relative_path_when_export_cache_path_then_appends_format_ext() -> None:
	# given
	library = "/lib"
	rel = "2025/photo.avif"
	# when
	jpeg = export_cache_path(library, rel, ExportFormat.JPEG)
	mp4 = export_cache_path(library, rel, ExportFormat.H264_AAC)
	# then
	assert jpeg.endswith("/.exports/2025/photo.avif.jpg")
	assert mp4.endswith("/.exports/2025/photo.avif.mp4")
	assert set(export_cache_paths_for_relative(library, rel)) == {jpeg, mp4}


def test_given_legacy_hash_name_when_check_then_recognized() -> None:
	# given
	legacy = "abcdef0123456789abcd.jpg"
	path_mirrored = "photo.avif.jpg"
	# when / then
	assert is_legacy_hash_export_filename(legacy) is True
	assert is_legacy_hash_export_filename(path_mirrored) is False
	assert is_legacy_hash_export_filename("not-a-hash.jpg") is False


def test_given_windows_separators_when_thumbnail_path_then_normalized(tmp_path: Path) -> None:
	# given
	library = str(tmp_path / "lib")
	# when
	thumb = thumbnail_path(library, r"2025\photo.avif")
	# then
	assert Path(thumb) == Path(library) / ".thumbnails" / "2025" / "photo.avif.jpg"
