from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_preview import STREAM_MAX_CHUNK_BYTES


class DeviceStreamErrorKind(StrEnum):
	"""Values are the ``detail`` codes of the loopback stream endpoint (see the device-file-picker spec)."""

	RANGE_REQUIRED = "range_required"
	RANGE_NOT_SATISFIABLE = "range_not_satisfiable"
	UNKNOWN_TOKEN = "unknown_token"  # noqa: S105 - an error code, not a secret


_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)", re.ASCII)


class DeviceStreamError(Exception):
	def __init__(self, kind: DeviceStreamErrorKind, detail: str = "") -> None:
		super().__init__(detail or kind.value)
		self.kind = kind
		self.detail = detail


@dataclass(frozen=True, slots=True)
class DeviceStreamGrant:
	"""What a stream token allows: read one phone file. ``path`` is normalized and storage-relative;
	``size`` is the real size from ``stat_file`` at mint time.
	"""

	method: ConnectionMethod
	device_id: str
	path: str
	size: int


@dataclass(frozen=True, slots=True)
class ByteRange:
	"""Inclusive byte range ``start..end`` of a file."""

	start: int
	end: int

	@property
	def length(self) -> int:
		return self.end - self.start + 1


@dataclass(frozen=True, slots=True)
class DeviceStreamChunk:
	"""One served range: ``data`` is bytes ``start..end`` (inclusive) of a ``total``-byte file."""

	data: bytes
	start: int
	end: int
	total: int


def parse_single_range(header: str | None, size: int, max_chunk: int = STREAM_MAX_CHUNK_BYTES) -> ByteRange:
	"""Resolve a ``Range`` header against a file of ``size`` bytes.

	Only one ``bytes=a-b`` or open-ended ``bytes=a-`` range is accepted. ``None``, malformed, suffix
	(``bytes=-n``) and multi-range headers raise ``DeviceStreamError(RANGE_REQUIRED)``; ``a >= size`` raises
	``RANGE_NOT_SATISFIABLE`` (``detail`` = the size). The result is truncated to ``max_chunk`` bytes and to ``size - 1``.
	"""
	match = _RANGE_RE.fullmatch(header or "")
	if match is None:
		raise DeviceStreamError(DeviceStreamErrorKind.RANGE_REQUIRED)
	start = int(match.group(1))
	end = int(match.group(2)) if match.group(2) else None
	if end is not None and end < start:
		raise DeviceStreamError(DeviceStreamErrorKind.RANGE_REQUIRED)
	if start >= size:
		raise DeviceStreamError(DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE, str(size))
	last = size - 1 if end is None else min(end, size - 1)
	return ByteRange(start, min(last, start + max_chunk - 1))


__all__ = [
	"ByteRange",
	"DeviceStreamChunk",
	"DeviceStreamError",
	"DeviceStreamErrorKind",
	"DeviceStreamGrant",
	"parse_single_range",
]
