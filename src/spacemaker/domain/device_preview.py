from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind
from spacemaker.domain.device_media import PREVIEWABLE_IMAGE_EXTENSIONS, PREVIEWABLE_VIDEO_EXTENSIONS


PREVIEW_HEAD_BYTES = 65_536
PREVIEW_FULL_PULL_MAX_BYTES = 25 * 1024 * 1024
PREVIEW_CACHE_MAX_BYTES = 200 * 1024 * 1024
PREVIEW_MAX_CONCURRENT_READS = 4
PREVIEW_HEAD_TIMEOUT_S = 10.0
PREVIEW_FULL_TIMEOUT_S = 30.0
DEVICE_PREVIEW_FORMAT_VERSION = "2"
"""Bump when the pipeline changes so old cache entries stop matching (``"2"``: video posters and durations)."""

STREAM_MAX_CHUNK_BYTES = 4 * 1024 * 1024
"""Largest byte range one loopback stream response serves (see ``parse_single_range``)."""
VIDEO_POSTER_TIMEOUT_S = 20.0
"""Wall-clock budget of one video poster render (first frame + duration)."""
PREVIEW_SLOT_WAIT_S = 20.0
"""Longest a preview request waits for one of the per-device read slots before answering ``TIMEOUT``."""
STREAM_READ_TIMEOUT_S = 10.0
"""Budget of one ``read_range`` device read (per range request)."""


class DevicePreviewMedia(StrEnum):
	"""Which pipeline renders a file's preview."""

	IMAGE = "image"
	VIDEO = "video"


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


class DevicePreviewCancelled(Exception):
	"""The caller went away (client abort) before the preview finished; nothing was cached."""


_ERROR_BY_BROWSE_KIND: dict[DeviceBrowseErrorKind, DevicePreviewErrorKind] = {
	DeviceBrowseErrorKind.INVALID_PATH: DevicePreviewErrorKind.INVALID_PATH,
	DeviceBrowseErrorKind.UNPLUGGED: DevicePreviewErrorKind.UNPLUGGED,
	DeviceBrowseErrorKind.UNAUTHORIZED: DevicePreviewErrorKind.UNAUTHORIZED,
	DeviceBrowseErrorKind.TIMEOUT: DevicePreviewErrorKind.TIMEOUT,
}


def map_browse_error(exc: DeviceBrowseError) -> DevicePreviewError:
	"""Preview-API error for a failed device read (anything unmapped, e.g. not found, is ``NO_PREVIEW``)."""
	kind = _ERROR_BY_BROWSE_KIND.get(exc.kind, DevicePreviewErrorKind.NO_PREVIEW)
	return DevicePreviewError(kind, exc.detail)


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
	duration_s: float | None = None
	"""Video length in seconds (``None`` for photos or when the container does not say)."""


@dataclass(frozen=True, slots=True)
class CachedDevicePreview:
	"""What ``DevicePreviewCachePort`` stores per key: the JPEG and, for videos, the duration."""

	jpeg: bytes
	duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class VideoPoster:
	"""First frame of a video as a fit-within JPEG, plus the duration found in the same run."""

	jpeg: bytes
	duration_s: float | None


def is_previewable_image(name: str) -> bool:
	"""True when the extension of ``name`` (case-insensitive) is in ``PREVIEWABLE_IMAGE_EXTENSIONS``."""
	if "." not in name:
		return False
	return name.rsplit(".", 1)[-1].lower() in PREVIEWABLE_IMAGE_EXTENSIONS


def preview_media_of(name: str) -> DevicePreviewMedia | None:
	"""``IMAGE`` / ``VIDEO`` from the extension of ``name`` (case-insensitive); ``None`` when not previewable."""
	if "." not in name:
		return None
	extension = name.rsplit(".", 1)[-1].lower()
	if extension in PREVIEWABLE_IMAGE_EXTENSIONS:
		return DevicePreviewMedia.IMAGE
	if extension in PREVIEWABLE_VIDEO_EXTENSIONS:
		return DevicePreviewMedia.VIDEO
	return None


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
	"PREVIEWABLE_VIDEO_EXTENSIONS",
	"STREAM_MAX_CHUNK_BYTES",
	"STREAM_READ_TIMEOUT_S",
	"VIDEO_POSTER_TIMEOUT_S",
	"CachedDevicePreview",
	"DevicePreviewMedia",
	"VideoPoster",
	"preview_media_of",
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
	"map_browse_error",
]
