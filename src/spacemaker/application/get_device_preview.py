from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import PurePosixPath

from spacemaker.application.device_stream_tokens import DeviceStreamTokens
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseError, normalize_browse_path
from spacemaker.domain.device_media import is_raw_name
from spacemaker.domain.device_preview import (
	PREVIEW_FULL_PULL_MAX_BYTES,
	PREVIEW_FULL_TIMEOUT_S,
	PREVIEW_HEAD_BYTES,
	PREVIEW_HEAD_TIMEOUT_S,
	PREVIEW_MAX_CONCURRENT_READS,
	PREVIEW_SLOT_WAIT_S,
	VIDEO_POSTER_TIMEOUT_S,
	CachedDevicePreview,
	DevicePreview,
	DevicePreviewCancelled,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewMedia,
	DevicePreviewRequest,
	VideoPoster,
	device_preview_cache_key,
	map_browse_error,
	preview_media_of,
)
from spacemaker.domain.device_stream import DeviceStreamGrant
from spacemaker.domain.dng_preview import (
	DNG_HEADER_READ_BYTES,
	DNG_HEADER_TIMEOUT_S,
	DNG_PREVIEW_TIMEOUT_S,
	ImageContainer,
	locate_dng_preview,
	sniff_container,
)
from spacemaker.ports.outbound.device_activity import DeviceActivityPort
from spacemaker.ports.outbound.device_preview_cache import DevicePreviewCachePort
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.preview_imaging import PreviewImagingPort
from spacemaker.ports.outbound.video_poster import VideoPosterPort


class GetDevicePreview:
	"""Photo thumbnail / lightbox rendition for one phone file.

	Strategy (see the device-file-picker spec): validate and normalize ``path`` and check the extension ->
	cache lookup (hit: no device call) -> ``DeviceActivityPort`` busy check (``DEVICE_BUSY``) -> take one of
	``PREVIEW_MAX_CONCURRENT_READS`` per-``(method, device_id)`` slots -> for ``THUMB``: head read, embedded
	thumbnail if present -> otherwise ``stat_file`` (real size, never the client's), over
	``PREVIEW_FULL_PULL_MAX_BYTES`` -> ``TOO_LARGE`` -> pull to a temp file -> ``render_jpeg`` -> delete the
	temp file in every outcome -> ``cache.put``. ``PREVIEW`` skips the head step. RAW (``.dng``) files are
	decided by content: the first ``DNG_HEADER_READ_BYTES`` say JPEG (photo strategy, temp file suffix
	``.jpg``), TIFF (locate the embedded JPEG from a few small reads, range-read just that, ``render_embedded_jpeg``;
	never fully pulled, never ``TOO_LARGE``) or neither (``NO_PREVIEW``). Raises
	``DevicePreviewError``; device failures from the repository (``DeviceBrowseError``) are mapped to
	``UNPLUGGED`` / ``UNAUTHORIZED`` / ``TIMEOUT`` / ``NO_PREVIEW`` (not found).

	``cancel`` (set when the client aborts) is checked before work starts, while waiting for a slot (the wait is
	bounded by ``slot_wait_s`` -> ``TIMEOUT``) and after getting one, and is handed to the poster renderer so
	ffmpeg is killed; a cancelled request raises ``DevicePreviewCancelled`` and caches nothing.

	``resolve_repository`` picks the ADB or AFC repository for a method, like ``devices_for`` does for
	``/api/device/list``.
	"""

	def __init__(
		self,
		resolve_repository: Callable[[ConnectionMethod], DeviceRepositoryPort],
		cache: DevicePreviewCachePort,
		imaging: PreviewImagingPort,
		activity: DeviceActivityPort,
		filesystem: FileSystemPort,
		*,
		poster: VideoPosterPort,
		tokens: DeviceStreamTokens,
		stream_url: Callable[[str], str],
		slot_wait_s: float = PREVIEW_SLOT_WAIT_S,
		slot_poll_s: float = 0.25,
		clock: Callable[[], float] = time.monotonic,
	) -> None:
		self._resolve_repository = resolve_repository
		self._cache = cache
		self._imaging = imaging
		self._activity = activity
		self._filesystem = filesystem
		self._poster = poster
		self._tokens = tokens
		self._stream_url = stream_url  # token -> loopback URL the poster renderer reads from
		self._slot_wait_s = slot_wait_s
		self._slot_poll_s = slot_poll_s
		self._clock = clock
		self._slots: dict[tuple[ConnectionMethod, str], threading.BoundedSemaphore] = {}
		self._slots_lock = threading.Lock()

	def _slot(self, method: ConnectionMethod, device_id: str) -> threading.BoundedSemaphore:
		with self._slots_lock:
			return self._slots.setdefault((method, device_id), threading.BoundedSemaphore(PREVIEW_MAX_CONCURRENT_READS))

	@contextmanager
	def _acquire_slot(self, method: ConnectionMethod, device_id: str, cancel: threading.Event | None) -> Iterator[None]:
		slot = self._slot(method, device_id)
		deadline = self._clock() + self._slot_wait_s
		while not slot.acquire(timeout=self._slot_poll_s):
			if cancel is not None and cancel.is_set():
				raise DevicePreviewCancelled
			if self._clock() >= deadline:
				raise DevicePreviewError(DevicePreviewErrorKind.TIMEOUT, "waiting for a free device read slot")
		try:
			if cancel is not None and cancel.is_set():
				raise DevicePreviewCancelled
			yield
		finally:
			slot.release()

	def __call__(self, request: DevicePreviewRequest, *, cancel: threading.Event | None = None) -> DevicePreview:
		try:
			path = normalize_browse_path(request.path)
		except DeviceBrowseError as exc:
			raise map_browse_error(exc) from exc
		media = preview_media_of(path.rsplit("/", 1)[-1])
		if media is None:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "not a previewable type")
		request = replace(request, path=path)  # same file, same cache key and ETag, however the client spelled the path
		key = device_preview_cache_key(request)
		etag = f'"{key}"'
		cached = self._cache.get(key)
		if cached is not None:
			return DevicePreview(cached.jpeg, etag, cached.duration_s)
		if cancel is not None and cancel.is_set():
			raise DevicePreviewCancelled
		if self._activity.is_busy(request.method, request.device_id):
			raise DevicePreviewError(DevicePreviewErrorKind.DEVICE_BUSY)
		repository = self._resolve_repository(request.method)
		with self._acquire_slot(request.method, request.device_id, cancel):
			try:
				if media is DevicePreviewMedia.VIDEO:
					poster = self._generate_video(repository, request, path, cancel)
					entry = CachedDevicePreview(poster.jpeg, poster.duration_s)
				elif is_raw_name(path.rsplit("/", 1)[-1]):
					entry = CachedDevicePreview(self._generate_raw(repository, request, path))
				else:
					entry = CachedDevicePreview(self._generate(repository, request, path))
			except DeviceBrowseError as exc:
				raise map_browse_error(exc) from exc
			except DevicePreviewError as exc:
				if cancel is not None and cancel.is_set():
					raise DevicePreviewCancelled from exc
				raise
		self._cache.put(key, entry)
		return DevicePreview(entry.jpeg, etag, entry.duration_s)

	def _generate_video(
		self, repository: DeviceRepositoryPort, request: DevicePreviewRequest, path: str, cancel: threading.Event | None
	) -> VideoPoster:
		"""Poster for a video: stat, mint a stream token for the file, ``render_poster`` against the loopback
		URL, revoke the token in every outcome. Videos are never ``TOO_LARGE`` (only ranges are read).
		"""
		stat = repository.stat_file(request.device_id, path)
		if stat.is_dir:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "not a file")
		token = self._tokens.mint(DeviceStreamGrant(request.method, request.device_id, path, stat.size))
		try:
			return self._poster.render_poster(
				self._stream_url(token), request.kind.max_edge, VIDEO_POSTER_TIMEOUT_S, cancel
			)
		finally:
			self._tokens.revoke(token)

	def _generate_raw(self, repository: DeviceRepositoryPort, request: DevicePreviewRequest, path: str) -> bytes:
		"""Preview of a ``.dng`` chosen by content: JPEG bytes -> photo strategy; TIFF -> embedded JPEG."""
		head = repository.read_head(request.device_id, path, DNG_HEADER_READ_BYTES, DNG_HEADER_TIMEOUT_S)
		container = sniff_container(head)
		if container is ImageContainer.JPEG:
			return self._generate(repository, request, path, suffix=".jpg")
		if container is not ImageContainer.TIFF:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "not a TIFF or JPEG")
		entry = repository.stat_file(request.device_id, path)
		if entry.is_dir:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "not a file")
		device_id = request.device_id
		location = locate_dng_preview(
			head,
			entry.size,
			lambda offset, length: repository.read_range(device_id, path, offset, length, DNG_HEADER_TIMEOUT_S),
		)
		if location is None:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "no embedded preview")
		jpeg = repository.read_range(device_id, path, location.offset, location.length, DNG_PREVIEW_TIMEOUT_S)
		if len(jpeg) != location.length or not jpeg.startswith(b"\xff\xd8"):
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "embedded preview unreadable")
		return self._imaging.render_embedded_jpeg(
			jpeg, request.kind.max_edge, location.orientation, PREVIEW_FULL_TIMEOUT_S
		)

	def _generate(
		self, repository: DeviceRepositoryPort, request: DevicePreviewRequest, path: str, *, suffix: str | None = None
	) -> bytes:
		edge = request.kind.max_edge
		if request.kind is DevicePreviewKind.THUMB:
			head = repository.read_head(request.device_id, path, PREVIEW_HEAD_BYTES, PREVIEW_HEAD_TIMEOUT_S)
			embedded = self._imaging.thumbnail_from_head(head, edge)
			if embedded is not None:
				return embedded
		entry = repository.stat_file(request.device_id, path)
		if entry.is_dir:
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "not a file")
		if entry.size > PREVIEW_FULL_PULL_MAX_BYTES:
			raise DevicePreviewError(DevicePreviewErrorKind.TOO_LARGE)
		if suffix is None:
			suffix = PurePosixPath(path).suffix.lower()  # Magick picks its decoder from this extension
		temp = self._filesystem.make_temp_file(suffix)
		try:
			repository.pull_file_with_timeout(request.device_id, path, temp, PREVIEW_FULL_TIMEOUT_S)
			return self._imaging.render_jpeg(temp, edge, PREVIEW_FULL_TIMEOUT_S)
		finally:
			self._filesystem.delete_file(temp)
