from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import replace
from pathlib import PurePosixPath

from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind, normalize_browse_path
from spacemaker.domain.device_preview import (
	PREVIEW_FULL_PULL_MAX_BYTES,
	PREVIEW_FULL_TIMEOUT_S,
	PREVIEW_HEAD_BYTES,
	PREVIEW_HEAD_TIMEOUT_S,
	PREVIEW_MAX_CONCURRENT_READS,
	DevicePreview,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
	device_preview_cache_key,
	is_previewable_image,
)
from spacemaker.ports.outbound.device_activity import DeviceActivityPort
from spacemaker.ports.outbound.device_preview_cache import DevicePreviewCachePort
from spacemaker.ports.outbound.device_repository import DeviceRepositoryPort
from spacemaker.ports.outbound.filesystem import FileSystemPort
from spacemaker.ports.outbound.preview_imaging import PreviewImagingPort


_ERROR_BY_BROWSE_KIND: dict[DeviceBrowseErrorKind, DevicePreviewErrorKind] = {
	DeviceBrowseErrorKind.INVALID_PATH: DevicePreviewErrorKind.INVALID_PATH,
	DeviceBrowseErrorKind.UNPLUGGED: DevicePreviewErrorKind.UNPLUGGED,
	DeviceBrowseErrorKind.UNAUTHORIZED: DevicePreviewErrorKind.UNAUTHORIZED,
	DeviceBrowseErrorKind.TIMEOUT: DevicePreviewErrorKind.TIMEOUT,
}


def _map_browse_error(exc: DeviceBrowseError) -> DevicePreviewError:
	kind = _ERROR_BY_BROWSE_KIND.get(exc.kind, DevicePreviewErrorKind.NO_PREVIEW)
	return DevicePreviewError(kind, exc.detail)


class GetDevicePreview:
	"""Photo thumbnail / lightbox rendition for one phone file.

	Strategy (see the device-file-picker spec): validate and normalize ``path`` and check the extension ->
	cache lookup (hit: no device call) -> ``DeviceActivityPort`` busy check (``DEVICE_BUSY``) -> take one of
	``PREVIEW_MAX_CONCURRENT_READS`` per-``(method, device_id)`` slots -> for ``THUMB``: head read, embedded
	thumbnail if present -> otherwise ``stat_file`` (real size, never the client's), over
	``PREVIEW_FULL_PULL_MAX_BYTES`` -> ``TOO_LARGE`` -> pull to a temp file -> ``render_jpeg`` -> delete the
	temp file in every outcome -> ``cache.put``. ``PREVIEW`` skips the head step. Raises
	``DevicePreviewError``; device failures from the repository (``DeviceBrowseError``) are mapped to
	``UNPLUGGED`` / ``UNAUTHORIZED`` / ``TIMEOUT`` / ``NO_PREVIEW`` (not found).

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
	) -> None:
		self._resolve_repository = resolve_repository
		self._cache = cache
		self._imaging = imaging
		self._activity = activity
		self._filesystem = filesystem
		self._slots: dict[tuple[ConnectionMethod, str], threading.BoundedSemaphore] = {}
		self._slots_lock = threading.Lock()

	def _slot(self, method: ConnectionMethod, device_id: str) -> threading.BoundedSemaphore:
		with self._slots_lock:
			return self._slots.setdefault((method, device_id), threading.BoundedSemaphore(PREVIEW_MAX_CONCURRENT_READS))

	def __call__(self, request: DevicePreviewRequest) -> DevicePreview:
		try:
			path = normalize_browse_path(request.path)
		except DeviceBrowseError as exc:
			raise _map_browse_error(exc) from exc
		if not is_previewable_image(path.rsplit("/", 1)[-1]):
			raise DevicePreviewError(DevicePreviewErrorKind.NO_PREVIEW, "not an image type")
		request = replace(request, path=path)  # same file, same cache key and ETag, however the client spelled the path
		key = device_preview_cache_key(request)
		etag = f'"{key}"'
		cached = self._cache.get(key)
		if cached is not None:
			return DevicePreview(cached, etag)
		if self._activity.is_busy(request.method, request.device_id):
			raise DevicePreviewError(DevicePreviewErrorKind.DEVICE_BUSY)
		repository = self._resolve_repository(request.method)
		with self._slot(request.method, request.device_id):
			try:
				jpeg = self._generate(repository, request, path)
			except DeviceBrowseError as exc:
				raise _map_browse_error(exc) from exc
		self._cache.put(key, jpeg)
		return DevicePreview(jpeg, etag)

	def _generate(self, repository: DeviceRepositoryPort, request: DevicePreviewRequest, path: str) -> bytes:
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
		suffix = PurePosixPath(path).suffix.lower()  # Magick picks its decoder from this extension
		temp = self._filesystem.make_temp_file(suffix)
		try:
			repository.pull_file_with_timeout(request.device_id, path, temp, PREVIEW_FULL_TIMEOUT_S)
			return self._imaging.render_jpeg(temp, edge, PREVIEW_FULL_TIMEOUT_S)
		finally:
			self._filesystem.delete_file(temp)
