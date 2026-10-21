"""Synthetic TIFF/DNG byte builders for tests (no real files, no device)."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


JPEG = b"\xff\xd8\xff\xe0preview-jpeg-bytes\xff\xd9"
_TYPES = {"B": 1, "H": 3, "I": 4}

# tag -> (type letter, values)
Entries = dict[int, tuple[str, list[int]]]


def jpeg_ifd(
	width: int,
	height: int,
	jpeg_offset: int,
	jpeg_length: int,
	*,
	orientation: int | None = None,
	strip: bool = True,
	compression: int = 7,
	photometric: int = 6,
	subfile_type: int | None = None,
	sub_ifds: list[int] | None = None,
) -> Entries:
	entries: Entries = {
		0x0100: ("I", [width]),
		0x0101: ("I", [height]),
		0x0102: ("H", [8, 8, 8]),
		0x0103: ("H", [compression]),
		0x0106: ("H", [photometric]),
	}
	if strip:
		entries[0x0111] = ("I", [jpeg_offset])
		entries[0x0117] = ("I", [jpeg_length])
	else:
		entries[0x0201] = ("I", [jpeg_offset])
		entries[0x0202] = ("I", [jpeg_length])
	if orientation is not None:
		entries[0x0112] = ("H", [orientation])
	if subfile_type is not None:
		entries[0x00FE] = ("I", [subfile_type])
	if sub_ifds is not None:
		entries[0x014A] = ("I", sub_ifds)
	return entries


def ifd_bytes(order: str, offset: int, entries: Entries, values_at: int | None = None) -> tuple[bytes, bytes, int]:
	"""An IFD at file ``offset``: (entry table, out-of-line values, file offset of those values). The values go
	right after the table unless ``values_at`` places them elsewhere (as Pixel tail-IFD0 files do, ~1.77 MB away)."""
	count = len(entries)
	table = struct.pack(order + "H", count)
	extra = b""
	extra_at = offset + 2 + 12 * count + 4 if values_at is None else values_at
	for tag in sorted(entries):
		letter, values = entries[tag]
		raw = struct.pack(f"{order}{len(values)}{letter}", *values)
		if len(raw) <= 4:
			field_bytes = raw.ljust(4, b"\0")
		else:
			field_bytes = struct.pack(order + "I", extra_at + len(extra))
			extra += raw
		table += struct.pack(order + "HHI", tag, _TYPES[letter], len(values)) + field_bytes
	return table + struct.pack(order + "I", 0), extra, extra_at


@dataclass
class DngFile:
	"""A fake file: ``data`` holds the real bytes, ``size`` the declared length (sparse beyond ``data``)."""

	data: bytes
	size: int
	reads: list[tuple[int, int]] = field(default_factory=list)

	@property
	def head(self) -> bytes:
		return self.data[:4096]

	def read_at(self, offset: int, length: int) -> bytes:
		self.reads.append((offset, length))
		return self.data[offset : offset + length]


def build_dng(
	order: str,
	ifds: list[tuple[int, Entries]],
	*,
	size: int | None = None,
	jpeg_at: int | None = None,
	jpeg: bytes = JPEG,
	ifd0_pointer: int | None = None,
	ifd0_values_at: int | None = None,
) -> DngFile:
	"""Header + the IFDs at their offsets (first one is IFD0) + ``jpeg`` at ``jpeg_at``. ``ifd0_values_at`` moves
	IFD0's out-of-line values away from its entry table."""
	magic = b"II*\x00" if order == "<" else b"MM\x00*"
	pointer = ifds[0][0] if ifd0_pointer is None else ifd0_pointer
	blobs = [(0, magic + struct.pack(order + "I", pointer))]
	for index, (offset, entries) in enumerate(ifds):
		table, extra, extra_at = ifd_bytes(order, offset, entries, ifd0_values_at if index == 0 else None)
		blobs += [(offset, table), (extra_at, extra)]
	if jpeg_at is not None:
		blobs.append((jpeg_at, jpeg))
	end = max(offset + len(blob) for offset, blob in blobs)
	data = bytearray(end)
	for offset, blob in blobs:
		data[offset : offset + len(blob)] = blob
	return DngFile(bytes(data), size if size is not None else len(data))
