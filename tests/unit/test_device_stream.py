# Video posters, domain rules (specs/device-file-picker/SPEC.md, "Video posters — API" and rules):
#   preview_media_of ........ video/image/other classification by extension (all 6 video formats, case-insensitive)
#   parse_single_range ...... single `bytes=a-b` / `bytes=a-`; truncation to 4 MiB and size-1;
#                             missing / malformed / suffix / multi -> 400 range_required; a >= size -> 416
# Seam for Phase 4: DeviceStreamError(RANGE_NOT_SATISFIABLE).detail is the decimal file size (the route
# renders it as `Content-Range: bytes */<size>`).
import pytest

from spacemaker.domain.device_preview import STREAM_MAX_CHUNK_BYTES, DevicePreviewMedia, preview_media_of
from spacemaker.domain.device_stream import ByteRange, DeviceStreamError, DeviceStreamErrorKind, parse_single_range


MEGABYTE = 1024 * 1024


@pytest.mark.parametrize("extension", ["mp4", "mov", "m4v", "3gp", "mkv", "webm"])
def test_given_video_extension_when_preview_media_of_then_video(extension: str) -> None:
	# given
	name = f"clip.{extension}"
	# when
	media = preview_media_of(name)
	# then
	assert media is DevicePreviewMedia.VIDEO


@pytest.mark.parametrize("name", ["CLIP.MP4", "Holiday.Mov", "a.b.WebM", "x.3GP"])
def test_given_mixed_case_video_name_when_preview_media_of_then_video(name: str) -> None:
	# given
	candidate = name
	# when
	media = preview_media_of(candidate)
	# then
	assert media is DevicePreviewMedia.VIDEO


@pytest.mark.parametrize("name", ["a.jpg", "a.JPEG", "a.png", "a.webp", "a.gif", "a.heic", "a.HEIF"])
def test_given_image_name_when_preview_media_of_then_image(name: str) -> None:
	# given
	candidate = name
	# when
	media = preview_media_of(candidate)
	# then
	assert media is DevicePreviewMedia.IMAGE


@pytest.mark.parametrize("name", ["a.dng", "a.txt", "README", "mp4", ".mp4x", "clip.mp4.bak", ""])
def test_given_other_name_when_preview_media_of_then_none(name: str) -> None:
	# given
	candidate = name
	# when
	media = preview_media_of(candidate)
	# then
	assert media is None


def test_given_closed_range_when_parse_then_inclusive_start_end() -> None:
	# given
	size = 10_000
	# when
	result = parse_single_range("bytes=100-199", size)
	# then
	assert result == ByteRange(100, 199)
	assert result.length == 100


def test_given_open_ended_range_when_parse_then_runs_to_chunk_cap() -> None:
	# given
	size = 100 * MEGABYTE
	# when
	result = parse_single_range("bytes=1000-", size)
	# then
	assert result == ByteRange(1000, 1000 + STREAM_MAX_CHUNK_BYTES - 1)


def test_given_open_ended_range_in_small_file_when_parse_then_truncated_to_last_byte() -> None:
	# given
	size = 500
	# when
	result = parse_single_range("bytes=100-", size)
	# then
	assert result == ByteRange(100, 499)


def test_given_end_past_file_when_parse_then_truncated_to_last_byte() -> None:
	# given
	size = 500
	# when
	result = parse_single_range("bytes=0-99999", size)
	# then
	assert result == ByteRange(0, 499)


def test_given_range_larger_than_cap_when_parse_then_truncated_to_4_mib() -> None:
	# given
	size = 100 * MEGABYTE
	# when
	result = parse_single_range("bytes=0-52428799", size)
	# then
	assert result == ByteRange(0, 4 * MEGABYTE - 1)
	assert result.length == 4 * MEGABYTE


def test_given_custom_max_chunk_when_parse_then_that_cap_applies() -> None:
	# given
	size = 1000
	# when
	result = parse_single_range("bytes=10-", size, max_chunk=100)
	# then
	assert result == ByteRange(10, 109)


def test_given_range_starting_at_last_byte_when_parse_then_one_byte() -> None:
	# given
	size = 500
	# when
	result = parse_single_range("bytes=499-", size)
	# then
	assert result == ByteRange(499, 499)


@pytest.mark.parametrize(
	"header",
	[
		None,
		"",
		"bytes=",
		"bytes=-500",
		"bytes=0-1,5-9",
		"bytes=abc-def",
		"items=0-9",
		"bytes=9-0",
		"bytes=0-9-",
		"0-9",
		"bytes=-",
	],
)
def test_given_missing_or_malformed_range_when_parse_then_range_required(header: str | None) -> None:
	# given
	size = 1000
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		parse_single_range(header, size)
	assert raised.value.kind is DeviceStreamErrorKind.RANGE_REQUIRED


@pytest.mark.parametrize("header", ["bytes=1000-", "bytes=1000-1500", "bytes=5000-"])
def test_given_start_at_or_past_size_when_parse_then_not_satisfiable_with_size_detail(header: str) -> None:
	# given
	size = 1000
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		parse_single_range(header, size)
	assert raised.value.kind is DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE
	assert raised.value.detail == "1000"


def test_given_empty_file_when_parse_then_not_satisfiable() -> None:
	# given
	size = 0
	# when / then
	with pytest.raises(DeviceStreamError) as raised:
		parse_single_range("bytes=0-", size)
	assert raised.value.kind is DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE
