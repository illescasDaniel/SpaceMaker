from __future__ import annotations

import struct
from dataclasses import dataclass


_SOI = b"\xff\xd8"
_EXIF_HEADER = b"Exif\x00\x00"
_TAG_ORIENTATION = 0x0112
_TAG_THUMB_OFFSET = 0x0201
_TAG_THUMB_LENGTH = 0x0202
_TYPE_SHORT = 3
_TYPE_LONG = 4
_MARKER_APP1 = 0xE1
_MARKER_SOS = 0xDA
_MARKER_EOI = 0xD9
_MAX_IFD_ENTRIES = 512


@dataclass(frozen=True, slots=True)
class ExifThumbnail:
	"""What the first bytes of a JPEG yield: the main image's Orientation (1-8, or ``None``) and the
	complete embedded thumbnail JPEG (``None`` when absent or cut off by the end of the data).
	"""

	orientation: int | None
	jpeg: bytes | None


def parse_exif_thumbnail(head: bytes) -> ExifThumbnail | None:
	"""Pure-Python read of the JPEG APP1/EXIF block; ``None`` for non-JPEG data or no usable EXIF. Never raises."""
	try:
		return _parse(head)
	except (struct.error, IndexError, ValueError):
		return None


def _parse(head: bytes) -> ExifThumbnail | None:
	if not head.startswith(_SOI):
		return None
	pos = 2
	while pos + 4 <= len(head):
		if head[pos] != 0xFF:
			return None
		marker = head[pos + 1]
		if marker == 0xFF:  # fill byte
			pos += 1
			continue
		if marker in (_MARKER_SOS, _MARKER_EOI):
			return None
		(length,) = struct.unpack_from(">H", head, pos + 2)
		if length < 2:
			return None
		body_start = pos + 4
		body_end = pos + 2 + length
		if marker == _MARKER_APP1 and head[body_start : body_start + 6] == _EXIF_HEADER:
			# A truncated segment still holds the TIFF directory; thumbnail completeness is checked below.
			return _parse_tiff(head[body_start + 6 : min(body_end, len(head))])
		pos = body_end
	return None


def _parse_tiff(tiff: bytes) -> ExifThumbnail | None:
	if len(tiff) < 8:
		return None
	if tiff[:2] == b"II":
		order = "<"
	elif tiff[:2] == b"MM":
		order = ">"
	else:
		return None
	(magic, ifd0) = struct.unpack_from(f"{order}HI", tiff, 2)
	if magic != 42:
		return None
	tags0, next_ifd = _read_ifd(tiff, ifd0, order)
	orientation = tags0.get(_TAG_ORIENTATION)
	if orientation is not None and not 1 <= orientation <= 8:
		orientation = None
	jpeg: bytes | None = None
	if next_ifd:
		tags1, _ = _read_ifd(tiff, next_ifd, order)
		offset = tags1.get(_TAG_THUMB_OFFSET)
		length = tags1.get(_TAG_THUMB_LENGTH)
		if offset is not None and length and offset + length <= len(tiff):
			candidate = tiff[offset : offset + length]
			if candidate.startswith(_SOI):
				jpeg = candidate
	return ExifThumbnail(orientation, jpeg)


def _read_ifd(tiff: bytes, offset: int, order: str) -> tuple[dict[int, int], int]:
	"""Tags with an inline SHORT/LONG value, plus the offset of the next IFD (0 = none)."""
	if offset < 8 or offset + 2 > len(tiff):
		return {}, 0
	(count,) = struct.unpack_from(f"{order}H", tiff, offset)
	if count > _MAX_IFD_ENTRIES:
		return {}, 0
	tags: dict[int, int] = {}
	cursor = offset + 2
	for _ in range(count):
		if cursor + 12 > len(tiff):
			return tags, 0
		tag, kind, items = struct.unpack_from(f"{order}HHI", tiff, cursor)
		if items == 1 and kind == _TYPE_SHORT:
			(tags[tag],) = struct.unpack_from(f"{order}H", tiff, cursor + 8)
		elif items == 1 and kind == _TYPE_LONG:
			(tags[tag],) = struct.unpack_from(f"{order}I", tiff, cursor + 8)
		cursor += 12
	if cursor + 4 > len(tiff):
		return tags, 0
	(next_ifd,) = struct.unpack_from(f"{order}I", tiff, cursor)
	return tags, next_ifd
