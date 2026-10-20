from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.connection import ConnectionMethod


PREVIEW_HEAD_BYTES = 65_536
PREVIEW_FULL_PULL_MAX_BYTES = 25 * 1024 * 1024
PREVIEW_CACHE_MAX_BYTES = 200 * 1024 * 1024
PREVIEW_MAX_CONCURRENT_READS = 4
PREVIEW_HEAD_TIMEOUT_S = 10.0
PREVIEW_FULL_TIMEOUT_S = 30.0
DEVICE_PREVIEW_FORMAT_VERSION = "1"
"""Bump when the pipeline changes so old cache entries stop matching."""

PREVIEWABLE_IMAGE_EXTENSIONS: frozenset[str] = frozenset({"jpg", "jpeg", "png", "webp", "gif", "heic", "heif"})
"""Lower-case, without the dot."""


class DevicePreviewKind(StrEnum):
	THUMB = "thumb"
	PREVIEW = "preview"

	@property
	def max_edge(self) -> int:
		"""Longest edge in pixels of the fit-within JPEG: 320 for ``THUMB``, 1600 for ``PREVIEW``."""
		return 320 if self is DevicePreviewKind.THUMB else 1600


class DevicePreviewErrorKind(StrEnum):
	"""Values are the ``detail`` codes of the preview API (see the device-file-picker spec)."""

	NO_PREVIEW = "no_preview"
	TOO_LARGE = "too_large"
	DEVICE_BUSY = "device_busy"
	UNPLUGGED = "unplugged"
	TIMEOUT = "timeout"
	UNAUTHORIZED = "unauthorized"
	INVALID_PATH = "invalid_path"


class DevicePreviewError(Exception):
	def __init__(self, kind: DevicePreviewErrorKind, detail: str = "") -> None:
		super().__init__(detail or kind.value)
		self.kind = kind
		self.detail = detail


@dataclass(frozen=True, slots=True)
class DevicePreviewRequest:
	"""One thumbnail/preview request. ``path`` is storage-relative (as in the listing); ``size`` and
	``mtime`` come from the client and only feed the cache key (the use case re-checks the real size).
	"""

	method: ConnectionMethod
	device_id: str
	path: str
	size: int
	mtime: int
	kind: DevicePreviewKind


@dataclass(frozen=True, slots=True)
class DevicePreview:
	"""A finished JPEG and its strong ``ETag`` (quoted, derived from the cache key)."""

	jpeg: bytes
	etag: str


def is_previewable_image(name: str) -> bool:
	"""True when the extension of ``name`` (case-insensitive) is in ``PREVIEWABLE_IMAGE_EXTENSIONS``."""
	if "." not in name:
		return False
	return name.rsplit(".", 1)[-1].lower() in PREVIEWABLE_IMAGE_EXTENSIONS


def device_preview_cache_key(request: DevicePreviewRequest) -> str:
	"""Stable hex digest of method, device id, path, size, mtime, kind and ``DEVICE_PREVIEW_FORMAT_VERSION``."""
	fields = (
		DEVICE_PREVIEW_FORMAT_VERSION,
		request.method.value,
		request.device_id,
		request.path,
		str(request.size),
		str(request.mtime),
		request.kind.value,
	)
	return hashlib.sha256("\x00".join(fields).encode("utf-8", errors="surrogatepass")).hexdigest()


__all__ = [
	"DEVICE_PREVIEW_FORMAT_VERSION",
	"PREVIEWABLE_IMAGE_EXTENSIONS",
	"PREVIEW_CACHE_MAX_BYTES",
	"PREVIEW_FULL_PULL_MAX_BYTES",
	"PREVIEW_FULL_TIMEOUT_S",
	"PREVIEW_HEAD_BYTES",
	"PREVIEW_HEAD_TIMEOUT_S",
	"PREVIEW_MAX_CONCURRENT_READS",
	"DevicePreview",
	"DevicePreviewError",
	"DevicePreviewErrorKind",
	"DevicePreviewKind",
	"DevicePreviewRequest",
	"device_preview_cache_key",
	"is_previewable_image",
]
