from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from functools import partial
from typing import TypeVar

import anyio
import anyio.to_thread
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.adapters.inbound.web.models import DeviceListBody
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import (
	DeviceBrowseError,
	DeviceBrowseErrorKind,
	DeviceBrowseQuery,
	parse_device_browse_sort,
)
from spacemaker.domain.device_preview import (
	DevicePreviewCancelled,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
)
from spacemaker.domain.device_stream import DeviceStreamError, DeviceStreamErrorKind


_STATUS_BY_KIND: dict[DeviceBrowseErrorKind, int] = {
	DeviceBrowseErrorKind.INVALID_PATH: 400,
	DeviceBrowseErrorKind.NOT_FOUND: 404,
	DeviceBrowseErrorKind.PERMISSION_DENIED: 403,
	DeviceBrowseErrorKind.UNAUTHORIZED: 403,
	DeviceBrowseErrorKind.UNPLUGGED: 409,
	DeviceBrowseErrorKind.TIMEOUT: 504,
	DeviceBrowseErrorKind.FAILED: 502,
	DeviceBrowseErrorKind.INVALID_CURSOR: 400,
}
_PREVIEW_STATUS_BY_KIND: dict[DevicePreviewErrorKind, int] = {
	DevicePreviewErrorKind.INVALID_PATH: 400,
	DevicePreviewErrorKind.NO_PREVIEW: 404,
	DevicePreviewErrorKind.DEVICE_BUSY: 409,
	DevicePreviewErrorKind.TOO_LARGE: 413,
	DevicePreviewErrorKind.UNPLUGGED: 503,
	DevicePreviewErrorKind.TIMEOUT: 503,
	DevicePreviewErrorKind.UNAUTHORIZED: 503,
}
_STREAM_STATUS_BY_KIND: dict[DeviceStreamErrorKind, int] = {
	DeviceStreamErrorKind.RANGE_REQUIRED: 400,
	DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE: 416,
	DeviceStreamErrorKind.UNKNOWN_TOKEN: 404,
}
_PREVIEW_CACHE_CONTROL = {"Cache-Control": "private, max-age=300, must-revalidate"}
_T = TypeVar("_T")
_DISCONNECT_POLL_S = 0.2
_STREAM_THREADS = 16
_CLIENT_CLOSED_STATUS = 499
_stream_limiter: anyio.CapacityLimiter | None = None


def _stream_capacity() -> anyio.CapacityLimiter:
	"""Own thread budget for ``/api/device/stream``: ffmpeg's sub-requests must never queue behind the preview
	requests that are waiting on them (created lazily, inside the running event loop).
	"""
	global _stream_limiter  # noqa: PLW0603
	if _stream_limiter is None:
		_stream_limiter = anyio.CapacityLimiter(_STREAM_THREADS)
	return _stream_limiter


async def _run_until_disconnect(request: Request, work: Callable[[threading.Event], _T]) -> _T:
	"""Run ``work(cancel)`` in a worker thread; ``cancel`` is set as soon as the client disconnects."""
	cancel = threading.Event()

	async def watch() -> None:
		while not await request.is_disconnected():
			await anyio.sleep(_DISCONNECT_POLL_S)
		cancel.set()

	failure: Exception | None = None
	results: list[_T] = []
	async with anyio.create_task_group() as group:
		group.start_soon(watch)
		try:
			results.append(await anyio.to_thread.run_sync(partial(work, cancel)))
		except Exception as exc:  # re-raised below, outside the group (which would wrap it in an ExceptionGroup)
			failure = exc
		finally:
			group.cancel_scope.cancel()
	if failure is not None:
		raise failure
	return results[0]


def _invalid_path() -> HTTPException:
	return HTTPException(status_code=400, detail=DevicePreviewErrorKind.INVALID_PATH.value)


def _preview_method(raw: str, device_id: str) -> ConnectionMethod:
	"""Same method/device checks as ``/api/device/list`` (any failure is ``invalid_path`` for the preview routes)."""
	try:
		method = ConnectionMethod(raw)
	except ValueError as exc:
		raise _invalid_path() from exc
	if method is ConnectionMethod.WIFI or (method is ConnectionMethod.AFC and sys.platform != "linux"):
		raise _invalid_path()
	if not device_id.strip():
		raise _invalid_path()
	return method


def build_device_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.post("/api/device/list")
	def device_list(request: Request, body: DeviceListBody) -> dict[str, object]:
		"""List one phone directory for the in-app picker (read-only; desktop-only like every module screen API)."""
		require_loopback(request)
		try:
			method = ConnectionMethod(body.method)
		except ValueError as exc:
			raise HTTPException(status_code=400, detail="unknown connection method") from exc
		if method is ConnectionMethod.WIFI:
			raise HTTPException(status_code=400, detail="the phone picker needs a USB connection")
		if method is ConnectionMethod.AFC and sys.platform != "linux":
			raise HTTPException(status_code=501, detail="iPhone USB is Linux only in this release")
		if not body.device_id.strip():
			raise HTTPException(status_code=400, detail="select a device")
		sort = parse_device_browse_sort(body.sort, body.order)
		try:
			page = services.list_device_directory(
				method,
				body.device_id,
				body.path,
				DeviceBrowseQuery(
					cursor=body.cursor,
					limit=body.limit,
					query=body.query,
					show_hidden=body.show_hidden,
					refresh=body.refresh,
					sort=sort,
				),
			)
		except DeviceBrowseError as exc:
			status = _STATUS_BY_KIND[exc.kind]
			raise HTTPException(status_code=status, detail={"error": exc.kind.value, "message": exc.detail}) from exc
		return {
			"path": page.path,
			"entries": [{"name": e.name, "is_dir": e.is_dir, "size": e.size, "mtime": e.mtime} for e in page.entries],
			"next_cursor": page.next_cursor,
			"total": page.total,
			"total_unfiltered": page.total_unfiltered,
			"sort": page.sort.key.value,
			"order": page.sort.order.value,
		}

	async def serve_preview(
		request: Request, kind: DevicePreviewKind, method: str, device_id: str, path: str, size: int, mtime: int
	) -> Response:
		require_loopback(request)
		preview_request = DevicePreviewRequest(_preview_method(method, device_id), device_id, path, size, mtime, kind)
		try:
			preview = await _run_until_disconnect(
				request, lambda cancel: services.get_device_preview(preview_request, cancel=cancel)
			)
		except DevicePreviewCancelled:
			return Response(status_code=_CLIENT_CLOSED_STATUS)  # the client is gone; nobody reads this
		except DevicePreviewError as exc:
			raise HTTPException(status_code=_PREVIEW_STATUS_BY_KIND[exc.kind], detail=exc.kind.value) from exc
		headers = {**_PREVIEW_CACHE_CONTROL, "ETag": preview.etag}
		if preview.duration_s is not None:
			headers["X-Media-Duration"] = str(preview.duration_s)
		header = request.headers.get("if-none-match")
		if header and preview.etag in {token.strip() for token in header.split(",")}:
			return Response(status_code=304, headers=headers)
		return Response(content=preview.jpeg, media_type="image/jpeg", headers=headers)

	@router.get("/api/device/thumb")
	async def device_thumb(
		request: Request,
		method: str,
		device_id: str,
		path: str,
		size: int = Query(ge=0),
		mtime: int = Query(ge=0),
	) -> Response:
		"""320 px JPEG of one phone photo (read-only; desktop-only)."""
		return await serve_preview(request, DevicePreviewKind.THUMB, method, device_id, path, size, mtime)

	@router.get("/api/device/preview")
	async def device_preview(
		request: Request,
		method: str,
		device_id: str,
		path: str,
		size: int = Query(ge=0),
		mtime: int = Query(ge=0),
	) -> Response:
		"""1600 px JPEG of one phone photo for the lightbox (read-only; desktop-only)."""
		return await serve_preview(request, DevicePreviewKind.PREVIEW, method, device_id, path, size, mtime)

	@router.get("/api/device/stream")
	async def device_stream(request: Request, token: str) -> Response:
		"""One byte range of a phone file for the local poster renderer (loopback-only, token-gated)."""
		require_loopback(request)
		try:
			range_header = request.headers.get("range")
			chunk = await anyio.to_thread.run_sync(
				partial(services.read_device_stream, token, range_header), limiter=_stream_capacity()
			)
		except DeviceStreamError as exc:
			headers = None
			if exc.kind is DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE:
				headers = {"Content-Range": f"bytes */{exc.detail}"}
			raise HTTPException(
				status_code=_STREAM_STATUS_BY_KIND[exc.kind], detail=exc.kind.value, headers=headers
			) from exc
		except DevicePreviewError as exc:
			raise HTTPException(status_code=_PREVIEW_STATUS_BY_KIND[exc.kind], detail=exc.kind.value) from exc
		return Response(
			content=chunk.data,
			status_code=206,
			media_type="application/octet-stream",
			headers={"Content-Range": f"bytes {chunk.start}-{chunk.end}/{chunk.total}", "Accept-Ranges": "bytes"},
		)

	return router
