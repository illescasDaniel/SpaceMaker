import logging

from tests.unit.fakes import FakeFileSystem, FakeMediaConverter, FakeMediaProbe

from spacemaker.application.convert_media import ConvertMedia
from spacemaker.domain.gallery_cache_paths import convert_staging_path
from spacemaker.domain.library import LibraryFolder
from spacemaker.domain.video_encode import HardwareVideoEncoder
from spacemaker.domain.web_compat import VideoProbe


def _paths(fs: FakeFileSystem, library: str, folder: LibraryFolder, rel: str) -> str:
	return fs.library_path(library, folder, rel)


def test_given_avif_in_originals_when_convert_then_moves_to_converted():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "x.avif"
	fs.files[_paths(fs, library, LibraryFolder.ORIGINALS, rel)] = 10
	probe = FakeMediaProbe()
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	use_case = ConvertMedia(fs, converter, probe)
	# when
	use_case.run(library)
	# then
	assert _paths(fs, library, LibraryFolder.ORIGINALS, rel) not in fs.files
	assert fs.files[_paths(fs, library, LibraryFolder.PROCESSED, rel)] == 10


def test_given_pdf_in_originals_when_convert_then_moves_to_invalid():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "doc.pdf"
	fs.files[_paths(fs, library, LibraryFolder.ORIGINALS, rel)] = 5
	use_case = ConvertMedia(fs, FakeMediaConverter(), FakeMediaProbe())
	# when
	use_case.run(library)
	# then
	assert fs.files[_paths(fs, library, LibraryFolder.INVALID, rel)] == 5


def test_given_png_when_encode_valid_then_removes_original():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "a.png"
	out_rel = "a.avif"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	dest = _paths(fs, library, LibraryFolder.PROCESSED, out_rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 100
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	probe.valid_images.add(staging)
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.output_sizes[staging] = 50
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert src not in fs.files
	assert fs.files[dest] == 50
	assert staging not in fs.files


def test_given_jpeg_pair_with_dng_when_convert_both_then_two_avifs():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	dng = _paths(fs, library, LibraryFolder.ORIGINALS, "photo.dng")
	jpg = _paths(fs, library, LibraryFolder.ORIGINALS, "photo.jpg")
	fs.files[dng] = 1000
	fs.files[jpg] = 200
	probe = FakeMediaProbe()
	probe.readable_images.update({dng, jpg})
	out_rel_dng = "photo.avif"
	out_rel_jpg = "photo_jpg.avif"
	out_dng = _paths(fs, library, LibraryFolder.PROCESSED, out_rel_dng)
	out_jpg = _paths(fs, library, LibraryFolder.PROCESSED, out_rel_jpg)
	staging_dng = convert_staging_path(library, out_rel_dng)
	staging_jpg = convert_staging_path(library, out_rel_jpg)
	probe.valid_images.update({staging_dng, staging_jpg})
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.output_sizes[staging_dng] = 80
	converter.output_sizes[staging_jpg] = 60
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert fs.files[out_dng] == 80
	assert fs.files[out_jpg] == 60
	assert dng not in fs.files
	assert jpg not in fs.files


def test_given_web_jpeg_and_oversized_avif_when_convert_then_keeps_jpeg_in_converted():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "web.jpg"
	out_rel = "web.avif"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	dest = _paths(fs, library, LibraryFolder.PROCESSED, out_rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 100
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	probe.valid_images.add(staging)
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.output_sizes[staging] = 120
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert dest not in fs.files
	assert staging not in fs.files
	assert fs.files[_paths(fs, library, LibraryFolder.PROCESSED, rel)] == 100


def test_given_encode_fails_twice_when_convert_then_moves_to_error():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "a.png"
	out_rel = "a.avif"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 10
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.fail_destinations.add(staging)
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert fs.files[_paths(fs, library, LibraryFolder.ERROR, rel)] == 10


def test_given_video_needing_encode_and_no_hw_when_convert_then_moves_to_converted():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "big.hevc.mp4"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	fs.files[src] = 500
	probe = FakeMediaProbe()
	probe.videos[src] = VideoProbe("mp4", "hevc", "aac", 5_000_000)
	converter = FakeMediaConverter(library_encoder=HardwareVideoEncoder.NONE)
	converter.bind_filesystem(fs)
	use_case = ConvertMedia(fs, converter, probe)
	# when
	use_case.run(library)
	# then
	assert fs.files[_paths(fs, library, LibraryFolder.PROCESSED, rel)] == 500
	assert not converter.encoded_videos
	assert "no hardware video encoder" in use_case.last_failure


def test_given_video_needing_encode_and_h264_hw_when_convert_then_h264_output():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "big.hevc.mp4"
	out_rel = "big.hevc.h264.mp4"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	dest = _paths(fs, library, LibraryFolder.PROCESSED, out_rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 500
	probe = FakeMediaProbe()
	probe.videos[src] = VideoProbe("mp4", "hevc", "aac", 5_000_000)
	probe.valid_videos.add(staging)
	converter = FakeMediaConverter(library_encoder=HardwareVideoEncoder.H264)
	converter.bind_filesystem(fs)
	converter.output_sizes[staging] = 200
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert fs.files[dest] == 200
	assert converter.encoded_h264 == [(src, staging)]


def test_given_low_bitrate_mp4_when_convert_then_move_as_is():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "small.mp4"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	fs.files[src] = 50
	probe = FakeMediaProbe()
	probe.videos[src] = VideoProbe("mp4", "h264", "aac", 1_000_000)
	# when
	ConvertMedia(fs, FakeMediaConverter(), probe).run(library)
	# then
	assert fs.files[_paths(fs, library, LibraryFolder.PROCESSED, rel)] == 50


def test_given_video_when_ffprobe_missing_then_moves_to_error_with_failure():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "clip.mp4"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	fs.files[src] = 80

	class ProbeMissing(FakeMediaProbe):
		def probe_video(self, path: str) -> VideoProbe | None:
			raise FileNotFoundError("Tool not found: ffprobe")

	use_case = ConvertMedia(fs, FakeMediaConverter(), ProbeMissing())
	# when
	use_case.run(library)
	# then
	assert fs.files[_paths(fs, library, LibraryFolder.ERROR, rel)] == 80
	assert "ffprobe" in use_case.last_failure


def test_given_png_when_encode_then_converter_receives_staging_path_not_processed():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "a.png"
	out_rel = "a.avif"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	dest = _paths(fs, library, LibraryFolder.PROCESSED, out_rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 100
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	probe.valid_images.add(staging)
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.output_sizes[staging] = 50
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert converter.encoded_images == [(src, staging)]
	assert dest != staging


def test_given_encode_fails_when_convert_then_processed_never_has_partial_output():
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "a.png"
	out_rel = "a.avif"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	dest = _paths(fs, library, LibraryFolder.PROCESSED, out_rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 10
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.fail_destinations.add(staging)
	# when
	ConvertMedia(fs, converter, probe).run(library)
	# then
	assert dest not in fs.files
	assert staging not in fs.files


def test_given_encode_fails_when_convert_then_logs_warning_with_relative_path(caplog):
	# given
	fs = FakeFileSystem()
	library = "/lib"
	rel = "a.png"
	out_rel = "a.avif"
	src = _paths(fs, library, LibraryFolder.ORIGINALS, rel)
	staging = convert_staging_path(library, out_rel)
	fs.files[src] = 10
	probe = FakeMediaProbe()
	probe.readable_images.add(src)
	converter = FakeMediaConverter()
	converter.bind_filesystem(fs)
	converter.fail_destinations.add(staging)
	# when
	with caplog.at_level(logging.WARNING, logger="spacemaker.application.convert_media"):
		ConvertMedia(fs, converter, probe).run(library)
	# then
	assert any(rel in record.message for record in caplog.records)
