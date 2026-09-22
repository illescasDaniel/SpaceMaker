from pathlib import Path

from tests.unit.fakes import FakeMediaConverter, FakeMediaProbe

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.domain.gallery_export import (
	ExportFormat,
	export_cache_filename,
	is_friendly_h264_aac_mp4,
	is_friendly_jpeg_filename,
	is_safe_gallery_relative_path,
)
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.web_compat import VideoProbe


def test_given_traversal_path_when_safe_check_then_false() -> None:
	# given
	path = "../secret.jpg"
	# when
	ok = is_safe_gallery_relative_path(path)
	# then
	assert ok is False


def test_given_jpeg_name_when_friendly_check_then_true() -> None:
	# given
	name = "photo.jpeg"
	# when
	# then
	assert is_friendly_jpeg_filename(name) is True


def test_given_h264_aac_probe_when_friendly_mp4_then_true() -> None:
	# given
	probe = VideoProbe(container_ext="mp4", video_codec="h264", audio_codec="aac", bitrate_bps=2_000_000)
	# when
	# then
	assert is_friendly_h264_aac_mp4(probe) is True


def test_given_avif_in_converted_when_export_jpeg_then_writes_cache(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.CONVERTED, "a.avif")
	Path(source).write_bytes(b"x" * 100)
	converter = FakeMediaConverter()
	use_case = ExportFriendlyMedia(fs, converter, FakeMediaProbe())
	# when
	result = use_case.run(library, "a.avif", ExportFormat.JPEG)
	# then
	assert len(converter.encoded_jpegs) == 1
	assert result.skipped_encode is False
	assert result.download_path.endswith(".jpg")


def test_given_jpeg_in_converted_when_export_jpeg_then_skips_encode(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.CONVERTED, "a.jpg")
	Path(source).write_bytes(b"x" * 100)
	converter = FakeMediaConverter()
	use_case = ExportFriendlyMedia(fs, converter, FakeMediaProbe())
	# when
	result = use_case.run(library, "a.jpg", ExportFormat.JPEG)
	# then
	assert converter.encoded_jpegs == []
	assert result.skipped_encode is True
	assert result.download_path == source


def test_given_stable_inputs_when_cache_filename_then_deterministic() -> None:
	# given
	# when
	a = export_cache_filename("x/y.avif", 1, 2, ExportFormat.JPEG)
	b = export_cache_filename("x/y.avif", 1, 2, ExportFormat.JPEG)
	# then
	assert a == b
	assert a.endswith(".jpg")
