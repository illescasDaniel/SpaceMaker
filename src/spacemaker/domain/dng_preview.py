"""Locating the JPEG preview embedded in a DNG from a few small byte-range reads (device-file-picker spec,
"RAW previews"). Pure and bounded: the bytes are untrusted, every malformed structure means "no preview", and
the only I/O goes through the ``read_at`` callable the caller passes in."""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


DNG_HEADER_READ_BYTES = 4096
"""Size of the first read at offset 0, and of each read at an IFD offset outside the bytes held."""
DNG_MAX_IFD_ENTRIES = 64
"""An IFD declaring more entries than this is malformed (no preview)."""
DNG_MAX_SUBIFDS = 8
"""At most this many SubIFDs (tag 0x014A) are read, each with one ``DNG_HEADER_READ_BYTES`` read."""
DNG_MAX_PREVIEW_BYTES = 8 * 1024 * 1024
"""A candidate JPEG longer than this is ignored."""
DNG_PREVIEW_MAX_EDGE = 1600
"""Pick the largest candidate whose long edge is at most this, else the smallest larger one."""
DNG_HEADER_TIMEOUT_S = 10.0
"""Budget of each header / IFD read."""
DNG_PREVIEW_TIMEOUT_S = 30.0
"""Budget of the preview range read."""


class ImageContainer(StrEnum):
	"""What the first bytes of a ``.dng`` file really are."""

	JPEG = "jpeg"
	"""Starts with ``FF D8`` (e.g. Snapseed saves JPEG bytes under a ``.dng`` name): use the photo strategy."""
	TIFF = "tiff"
	"""Starts with ``II*\\0`` or ``MM\\0*``: parse the IFDs for an embedded JPEG."""
	UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DngPreviewCandidate:
	"""One IFD describing a displayable JPEG (Photometric 6, 8-bit when that is held, Compression 6/7,
	NewSubfileType 0/1, single strip or JPEGInterchangeFormat)."""

	offset: int
	length: int
	width: int
	height: int

	@property
	def long_edge(self) -> int:
		return max(self.width, self.height)


@dataclass(frozen=True, slots=True)
class DngPreviewLocation:
	"""The chosen JPEG's byte range plus the DNG's IFD0 Orientation (1-8; 1 when absent or invalid), applied only
	when the JPEG has no EXIF Orientation of its own."""

	offset: int
	length: int
	width: int
	height: int
	orientation: int


def sniff_container(head: bytes) -> ImageContainer:
	"""``JPEG`` / ``TIFF`` / ``UNKNOWN`` from the first bytes (fewer than 4 bytes -> ``UNKNOWN``)."""
	if len(head) < 4:
		return ImageContainer.UNKNOWN
	if head[:2] == b"\xff\xd8":
		return ImageContainer.JPEG
	if head[:4] in (b"II*\x00", b"MM\x00*"):
		return ImageContainer.TIFF
	return ImageContainer.UNKNOWN


def pick_dng_preview(
	candidates: list[DngPreviewCandidate], max_edge: int = DNG_PREVIEW_MAX_EDGE
) -> DngPreviewCandidate | None:
	"""Largest candidate with ``long_edge <= max_edge``; if none, the smallest larger one; ``None`` when empty.
	Ties keep the first in IFD order."""
	if not candidates:
		return None
	within = [c for c in candidates if c.long_edge <= max_edge]
	if within:
		best = within[0]
		for candidate in within[1:]:
			if candidate.long_edge > best.long_edge:
				best = candidate
		return best
	best = candidates[0]
	for candidate in candidates[1:]:
		if candidate.long_edge < best.long_edge:
			best = candidate
	return best


_TAG_NEW_SUBFILE_TYPE = 0x00FE
_TAG_WIDTH = 0x0100
_TAG_HEIGHT = 0x0101
_TAG_BITS_PER_SAMPLE = 0x0102
_TAG_COMPRESSION = 0x0103
_TAG_PHOTOMETRIC = 0x0106
_TAG_STRIP_OFFSETS = 0x0111
_TAG_ORIENTATION = 0x0112
_TAG_STRIP_BYTE_COUNTS = 0x0117
_TAG_SUB_IFDS = 0x014A
_TAG_JPEG_OFFSET = 0x0201
_TAG_JPEG_LENGTH = 0x0202
_TYPE_SIZES = {1: 1, 3: 2, 4: 4}  # BYTE, SHORT, LONG: the only types this parser reads
_FORMATS = {1: "B", 3: "H", 4: "I"}
_PHOTOMETRIC_YCBCR = 6
_JPEG_COMPRESSIONS = (6, 7)
_ENTRY_SIZE = 12


class _Malformed(Exception):
	"""Internal: the bytes are not a well-formed DNG structure (mapped to "no preview")."""


class _Entry:
	__slots__ = ("count", "field_offset", "type")

	def __init__(self, type_: int, count: int, field_offset: int) -> None:
		self.type = type_
		self.count = count
		self.field_offset = field_offset  # absolute-in-buffer offset of the 4-byte value field


class _Ifd:
	"""One parsed IFD: its entries plus the bytes it was read from (for values stored out of line)."""

	def __init__(self, buf: bytes, base: int, order: str, entries: dict[int, _Entry], file_size: int) -> None:
		self._buf = buf
		self._base = base  # file offset of buf[0]
		self._order = order
		self.entries = entries
		self._file_size = file_size

	def values(self, tag: int) -> list[int] | None:
		"""Integer values of ``tag``; ``None`` when absent, of an unsupported type or stored outside the held bytes."""
		entry = self.entries.get(tag)
		if entry is None:
			return None
		size = _TYPE_SIZES.get(entry.type)
		if size is None or entry.count < 1 or entry.count > DNG_MAX_IFD_ENTRIES * 4:
			return None
		total = size * entry.count
		if total <= 4:
			raw_start = entry.field_offset
		else:
			target = struct.unpack_from(self._order + "I", self._buf, entry.field_offset)[0] - self._base
			if target < 0:
				return None
			raw_start = target
		if raw_start + total > len(self._buf):
			return None
		fmt = f"{self._order}{entry.count}{_FORMATS[entry.type]}"
		return list(struct.unpack_from(fmt, self._buf, raw_start))

	def out_of_reach(self, tag: int) -> bool:
		"""``tag`` is present with a supported type, but its values lie in the file outside the held bytes."""
		entry = self.entries.get(tag)
		if entry is None or entry.type not in _TYPE_SIZES or entry.count < 1:
			return False
		total = _TYPE_SIZES[entry.type] * entry.count
		if total <= 4:
			return False
		absolute = struct.unpack_from(self._order + "I", self._buf, entry.field_offset)[0]
		target = absolute - self._base
		held = 0 <= target and target + total <= len(self._buf)
		return not held and absolute + total <= self._file_size

	def first(self, tag: int) -> int | None:
		values = self.values(tag)
		return values[0] if values else None


def _parse_ifd(
	offset: int,
	order: str,
	head: bytes,
	file_size: int,
	read_at: Callable[[int, int], bytes],
	*,
	force_read: bool,
) -> _Ifd:
	if offset < 8 or offset + 2 > file_size:
		raise _Malformed
	buf = head
	base = 0
	held = not force_read and offset + 2 <= len(head)
	if held:
		count = struct.unpack_from(order + "H", head, offset)[0]
		if count > DNG_MAX_IFD_ENTRIES:
			raise _Malformed
		held = offset + 2 + count * _ENTRY_SIZE <= len(head)
	if not held:
		length = min(DNG_HEADER_READ_BYTES, file_size - offset)
		buf = read_at(offset, length)
		base = offset
		if len(buf) < 2:
			raise _Malformed
	start = offset - base
	count = struct.unpack_from(order + "H", buf, start)[0]
	if count > DNG_MAX_IFD_ENTRIES or start + 2 + count * _ENTRY_SIZE > len(buf):
		raise _Malformed
	entries: dict[int, _Entry] = {}
	for index in range(count):
		position = start + 2 + index * _ENTRY_SIZE
		tag, type_, entry_count = struct.unpack_from(order + "HHI", buf, position)
		entries.setdefault(tag, _Entry(type_, entry_count, position + 8))
	return _Ifd(buf, base, order, entries, file_size)


def _candidate_of(ifd: _Ifd, file_size: int) -> DngPreviewCandidate | None:
	if ifd.first(_TAG_PHOTOMETRIC) != _PHOTOMETRIC_YCBCR:
		return None
	if ifd.first(_TAG_COMPRESSION) not in _JPEG_COMPRESSIONS:
		return None
	# Pixel tail-IFD0 files keep BitsPerSample ~1.77 MB away: not fetched (the FF D8 check and Magick still guard).
	if not ifd.out_of_reach(_TAG_BITS_PER_SAMPLE):
		bits = ifd.values(_TAG_BITS_PER_SAMPLE)
		if not bits or any(bit != 8 for bit in bits):
			return None
	subfile = ifd.first(_TAG_NEW_SUBFILE_TYPE) if _TAG_NEW_SUBFILE_TYPE in ifd.entries else 0
	if subfile not in (0, 1):
		return None
	width = ifd.first(_TAG_WIDTH)
	height = ifd.first(_TAG_HEIGHT)
	if not width or not height:
		return None
	strip_offsets = ifd.values(_TAG_STRIP_OFFSETS)
	strip_counts = ifd.values(_TAG_STRIP_BYTE_COUNTS)
	if strip_offsets is not None and strip_counts is not None:
		if len(strip_offsets) != 1 or len(strip_counts) != 1:
			return None
		offset, length = strip_offsets[0], strip_counts[0]
	else:
		jpeg_offset = ifd.first(_TAG_JPEG_OFFSET)
		jpeg_length = ifd.first(_TAG_JPEG_LENGTH)
		if jpeg_offset is None or jpeg_length is None:
			return None
		offset, length = jpeg_offset, jpeg_length
	if length <= 0 or length > DNG_MAX_PREVIEW_BYTES or offset < 8 or offset + length > file_size:
		return None
	return DngPreviewCandidate(offset, length, width, height)


def locate_dng_preview(head: bytes, file_size: int, read_at: Callable[[int, int], bytes]) -> DngPreviewLocation | None:
	"""Find the JPEG preview of a TIFF-based DNG.

	``head`` is the first ``DNG_HEADER_READ_BYTES`` of the file and ``file_size`` its real size (from the
	device, never the client). ``read_at(offset, length)`` reads more bytes; it is called only with ranges inside
	``file_size``: once at the IFD0 offset when IFD0 lies outside ``head``, and once per SubIFD (at most
	``DNG_MAX_SUBIFDS``) only when IFD0 is not itself a candidate. It never reads image data.

	Returns ``None`` (never raises) for anything malformed: truncated or non-TIFF header, an IFD with more than
	``DNG_MAX_IFD_ENTRIES`` entries, an IFD visited twice, offsets/lengths outside ``file_size``, no candidate, or
	a candidate longer than ``DNG_MAX_PREVIEW_BYTES``. Exceptions raised by ``read_at`` itself (device errors)
	propagate unchanged. Both byte orders are supported.
	"""
	if sniff_container(head) is not ImageContainer.TIFF or file_size < 8:
		return None
	order = "<" if head[:2] == b"II" else ">"
	try:
		return _locate(head, order, file_size, read_at)
	except (_Malformed, struct.error):
		return None


def _locate(head: bytes, order: str, file_size: int, read_at: Callable[[int, int], bytes]) -> DngPreviewLocation | None:
	if len(head) < 8:
		return None
	visited: set[int] = set()
	ifd0_offset = struct.unpack_from(order + "I", head, 4)[0]
	visited.add(ifd0_offset)
	ifd0 = _parse_ifd(ifd0_offset, order, head, file_size, read_at, force_read=False)
	orientation = ifd0.first(_TAG_ORIENTATION)
	if orientation is None or not 1 <= orientation <= 8:
		orientation = 1
	candidate = _candidate_of(ifd0, file_size)
	if candidate is None:
		candidates: list[DngPreviewCandidate] = []
		for sub_offset in (ifd0.values(_TAG_SUB_IFDS) or [])[:DNG_MAX_SUBIFDS]:
			if sub_offset in visited:
				raise _Malformed
			visited.add(sub_offset)
			sub = _parse_ifd(sub_offset, order, head, file_size, read_at, force_read=True)
			found = _candidate_of(sub, file_size)
			if found is not None:
				candidates.append(found)
		candidate = pick_dng_preview(candidates)
	if candidate is None:
		return None
	return DngPreviewLocation(candidate.offset, candidate.length, candidate.width, candidate.height, orientation)


__all__ = [
	"DNG_HEADER_READ_BYTES",
	"DNG_HEADER_TIMEOUT_S",
	"DNG_MAX_IFD_ENTRIES",
	"DNG_MAX_PREVIEW_BYTES",
	"DNG_MAX_SUBIFDS",
	"DNG_PREVIEW_MAX_EDGE",
	"DNG_PREVIEW_TIMEOUT_S",
	"DngPreviewCandidate",
	"DngPreviewLocation",
	"ImageContainer",
	"locate_dng_preview",
	"pick_dng_preview",
	"sniff_container",
]
