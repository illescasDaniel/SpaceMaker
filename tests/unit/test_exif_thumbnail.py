import struct

import pytest

from spacemaker.adapters.outbound.media.exif_thumbnail import ExifThumbnail, parse_exif_thumbnail
from spacemaker.adapters.outbound.media.subprocess_preview_imaging import SubprocessPreviewImaging


THUMB = b"\xff\xd8\xff\xdb-tiny-thumbnail-\xff\xd9"


def _tiff(order: str, orientation: int | None, thumb: bytes | None, *, thumb_length: int | None = None) -> bytes:
	"""TIFF block: IFD0 (Orientation) -> IFD1 (JPEGInterchangeFormat / Length) -> thumbnail bytes."""
	tag0 = [(0x0112, 3, orientation)] if orientation is not None else []
	ifd0_size = 2 + 12 * len(tag0) + 4
	ifd1_at = 8 + ifd0_size
	tags1 = [] if thumb is None else [(0x0201, 4, 0), (0x0202, 4, len(thumb) if thumb_length is None else thumb_length)]
	ifd1_size = 2 + 12 * len(tags1) + 4
	thumb_at = ifd1_at + ifd1_size
	tags1 = [(tag, kind, thumb_at if tag == 0x0201 else value) for tag, kind, value in tags1]

	def entry(tag: int, kind: int, value: int) -> bytes:
		fmt = f"{order}HHI" + ("H2x" if kind == 3 else "I")
		return struct.pack(fmt, tag, kind, 1, value)

	out = b"II*\x00" if order == "<" else b"MM\x00*"
	out += struct.pack(f"{order}I", 8)
	out += struct.pack(f"{order}H", len(tag0)) + b"".join(entry(*t) for t in tag0)
	out += struct.pack(f"{order}I", ifd1_at if tags1 else 0)
	if tags1:
		out += struct.pack(f"{order}H", len(tags1)) + b"".join(entry(*t) for t in tags1)
		out += struct.pack(f"{order}I", 0)
		out += thumb or b""
	return out


def _jpeg(tiff: bytes) -> bytes:
	app1 = b"Exif\x00\x00" + tiff
	return b"\xff\xd8" + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1 + b"\xff\xda\x00\x02rest-of-image"


@pytest.mark.parametrize("order", ["<", ">"])
def test_given_exif_with_thumb_when_parse_then_orientation_and_thumbnail(order: str) -> None:
	# given
	head = _jpeg(_tiff(order, 6, THUMB))
	# when
	result = parse_exif_thumbnail(head)
	# then
	assert result == ExifThumbnail(6, THUMB)


def test_given_exif_without_ifd1_when_parse_then_orientation_only() -> None:
	# given
	head = _jpeg(_tiff("<", 3, None))
	# when
	result = parse_exif_thumbnail(head)
	# then
	assert result == ExifThumbnail(3, None)


def test_given_thumbnail_cut_off_by_head_when_parse_then_no_thumbnail() -> None:
	# given
	head = _jpeg(_tiff("<", 1, THUMB))
	cut = head[: head.index(b"tiny") + 3]
	# when
	result = parse_exif_thumbnail(cut)
	# then
	assert result is not None
	assert result.jpeg is None


def test_given_thumbnail_length_beyond_segment_when_parse_then_no_thumbnail() -> None:
	# given
	head = _jpeg(_tiff("<", 1, THUMB, thumb_length=5000))
	# when
	result = parse_exif_thumbnail(head)
	# then
	assert result == ExifThumbnail(1, None)


def test_given_out_of_range_orientation_when_parse_then_orientation_none() -> None:
	# given
	head = _jpeg(_tiff("<", 9, THUMB))
	# when
	result = parse_exif_thumbnail(head)
	# then
	assert result == ExifThumbnail(None, THUMB)


@pytest.mark.parametrize(
	"head",
	[
		b"",
		b"\x89PNG\r\n\x1a\n" + b"x" * 100,
		b"\xff\xd8",
		b"\xff\xd8\xff\xe1\x00",
		b"\xff\xd8\xff\xda\x00\x02",
		b"\xff\xd8garbage",
	],
)
def test_given_non_jpeg_or_no_exif_when_parse_then_none(head: bytes) -> None:
	# given
	# when
	result = parse_exif_thumbnail(head)
	# then
	assert result is None


def test_given_corrupt_exif_when_parse_then_none_without_raising() -> None:
	# given
	app1 = b"Exif\x00\x00" + b"II*\x00" + struct.pack("<I", 0xFFFFFF)
	head = b"\xff\xd8\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
	# when
	result = parse_exif_thumbnail(head)
	# then
	assert result is None or result.jpeg is None


class _CapturingImaging(SubprocessPreviewImaging):
	def __init__(self) -> None:
		super().__init__()
		self.calls: list[tuple[list[str], bytes | None]] = []

	def _run_magick(self, args: list[str], stdin: bytes | None, timeout_s: float) -> bytes:
		self.calls.append((args, stdin))
		return b"out-jpeg"


@pytest.mark.parametrize(("orientation", "name"), [(6, "RightTop"), (3, "BottomRight"), (8, "LeftBottom")])
def test_given_rotated_photo_when_thumbnail_from_head_then_magick_gets_orientation(orientation: int, name: str) -> None:
	# given
	imaging = _CapturingImaging()
	head = _jpeg(_tiff("<", orientation, THUMB))
	# when
	result = imaging.thumbnail_from_head(head, 320)
	# then
	args, stdin = imaging.calls[0]
	assert result == b"out-jpeg"
	assert stdin == THUMB
	assert args[args.index("-orient") + 1] == name
	assert "320x320>" in args


def test_given_upright_photo_when_thumbnail_from_head_then_no_orient_flag() -> None:
	# given
	imaging = _CapturingImaging()
	head = _jpeg(_tiff("<", 1, THUMB))
	# when
	imaging.thumbnail_from_head(head, 320)
	# then
	assert "-orient" not in imaging.calls[0][0]


def test_given_head_without_thumbnail_when_thumbnail_from_head_then_none_and_no_subprocess() -> None:
	# given
	imaging = _CapturingImaging()
	# when
	result = imaging.thumbnail_from_head(b"\x89PNG" + b"x" * 50, 320)
	# then
	assert result is None
	assert imaging.calls == []
