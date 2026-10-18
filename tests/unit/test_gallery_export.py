import os
from pathlib import Path

import pytest
from tests.unit.fakes import FakeMediaConverter, FakeMediaProbe

from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.export_friendly_media import ExportFriendlyMedia
from spacemaker.domain.gallery_batch import CpuEncodeConfirmationRequired, VideoExportEncoder
from spacemaker.domain.gallery_cache_paths import export_cache_path
from spacemaker.domain.gallery_export import (
	ExportFormat,
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


def test_given_avif_in_converted_when_export_jpeg_then_writes_path_mirrored_cache(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.PROCESSED, "a.avif")
	Path(source).write_bytes(b"x" * 100)
	converter = FakeMediaConverter()
	use_case = ExportFriendlyMedia(fs, converter, FakeMediaProbe())
	expected = export_cache_path(library, "a.avif", ExportFormat.JPEG)
	# when
	result = use_case.run(library, "a.avif", ExportFormat.JPEG)
	# then
	assert len(converter.encoded_jpegs) == 1
	assert result.skipped_encode is False
	assert result.download_path == str(Path(expected).resolve())
	assert Path(expected).is_file()


def test_given_jpeg_in_converted_when_export_jpeg_then_skips_encode(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.PROCESSED, "a.jpg")
	Path(source).write_bytes(b"x" * 100)
	converter = FakeMediaConverter()
	use_case = ExportFriendlyMedia(fs, converter, FakeMediaProbe())
	# when
	result = use_case.run(library, "a.jpg", ExportFormat.JPEG)
	# then
	assert converter.encoded_jpegs == []
	assert result.skipped_encode is True
	assert result.download_path == source


def test_given_fresh_cache_when_export_jpeg_then_reuses_without_reencode(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.PROCESSED, "a.avif")
	Path(source).write_bytes(b"x" * 100)
	cache = Path(export_cache_path(library, "a.avif", ExportFormat.JPEG))
	cache.parent.mkdir(parents=True, exist_ok=True)
	cache.write_bytes(b"cached")
	# Ensure cache is not older than source.
	os.utime(cache, (Path(source).stat().st_mtime + 1, Path(source).stat().st_mtime + 1))
	converter = FakeMediaConverter()
	use_case = ExportFriendlyMedia(fs, converter, FakeMediaProbe())
	# when
	result = use_case.run(library, "a.avif", ExportFormat.JPEG)
	# then
	assert converter.encoded_jpegs == []
	assert result.skipped_encode is False
	assert result.download_path == str(cache.resolve())


def test_given_windows_drive_path_when_gallery_path_checked_then_unsafe():
	# given
	paths = ["C:/Windows/evil.jpg", "C:evil.jpg", "2025/a.avif"]
	# when
	results = [is_safe_gallery_relative_path(path) for path in paths]
	# then
	assert results == [False, False, True]


def test_given_encode_fails_midway_when_export_jpeg_then_no_cache_file_or_partial_left(tmp_path) -> None:
	# given
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.PROCESSED, "a.avif")
	Path(source).write_bytes(b"x" * 100)

	class _Crashing(FakeMediaConverter):
		def encode_image_to_jpeg(self, source: str, destination: str) -> None:
			Path(destination).write_bytes(b"half")
			raise RuntimeError("magick crashed")

	use_case = ExportFriendlyMedia(fs, _Crashing(), FakeMediaProbe())
	cache = Path(export_cache_path(library, "a.avif", ExportFormat.JPEG))
	# when
	with pytest.raises(RuntimeError):
		use_case.run(library, "a.avif", ExportFormat.JPEG)
	# then
	assert not cache.exists()
	assert list(cache.parent.glob("*")) == []


def _video_env(tmp_path, encoder: VideoExportEncoder):
	library = str(tmp_path / "lib")
	fs = LocalFileSystem()
	fs.ensure_library_folders(library)
	source = fs.library_path(library, LibraryFolder.PROCESSED, "v.av1.mp4")
	Path(source).write_bytes(b"x" * 100)
	converter = FakeMediaConverter(friendly_encoder=encoder)
	return library, converter, ExportFriendlyMedia(fs, converter, FakeMediaProbe())


def test_given_no_hardware_but_cpu_when_export_mp4_unconfirmed_then_confirmation_required(tmp_path) -> None:
	# given
	library, converter, use_case = _video_env(tmp_path, VideoExportEncoder.CPU_H264)
	# when
	# then
	with pytest.raises(CpuEncodeConfirmationRequired) as info:
		use_case.run(library, "v.av1.mp4", ExportFormat.H264_AAC)
	assert info.value.video_count == 1
	assert converter.encoded_h264 == []


def test_given_no_hardware_but_cpu_when_export_mp4_confirmed_then_encodes_on_cpu(tmp_path) -> None:
	# given
	library, converter, use_case = _video_env(tmp_path, VideoExportEncoder.CPU_H264)
	# when
	result = use_case.run(library, "v.av1.mp4", ExportFormat.H264_AAC, allow_cpu_encode=True)
	# then
	assert converter.h264_use_cpu_flags == [True]
	assert result.skipped_encode is False


def test_given_hardware_when_export_mp4_then_no_confirmation_and_not_cpu(tmp_path) -> None:
	# given
	library, converter, use_case = _video_env(tmp_path, VideoExportEncoder.HARDWARE_H264)
	# when
	use_case.run(library, "v.av1.mp4", ExportFormat.H264_AAC)
	# then
	assert converter.h264_use_cpu_flags == [False]


def test_given_no_encoder_when_export_mp4_then_error_without_encode(tmp_path) -> None:
	# given
	library, converter, use_case = _video_env(tmp_path, VideoExportEncoder.NONE)
	# when
	# then
	with pytest.raises(ValueError, match="not available"):
		use_case.run(library, "v.av1.mp4", ExportFormat.H264_AAC, allow_cpu_encode=True)
	assert converter.encoded_h264 == []


def test_given_no_hardware_and_friendly_source_when_export_mp4_then_no_prompt(tmp_path) -> None:
	# given
	library, converter, use_case = _video_env(tmp_path, VideoExportEncoder.CPU_H264)
	source = str(Path(library) / "processed" / "v.av1.mp4")
	use_case._probe.videos[source] = VideoProbe(  # type: ignore[attr-defined]
		container_ext="mp4", video_codec="h264", audio_codec="aac", bitrate_bps=1_000_000
	)
	# when
	result = use_case.run(library, "v.av1.mp4", ExportFormat.H264_AAC)
	# then
	assert result.skipped_encode is True
	assert converter.encoded_h264 == []
