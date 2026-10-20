from __future__ import annotations

import sys

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
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
)


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
_PREVIEW_CACHE_CONTROL = {"Cache-Control": "private, max-age=300, must-revalidate"}


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

	def serve_preview(
		request: Request, kind: DevicePreviewKind, method: str, device_id: str, path: str, size: int, mtime: int
	) -> Response:
		require_loopback(request)
		preview_request = DevicePreviewRequest(_preview_method(method, device_id), device_id, path, size, mtime, kind)
		try:
			preview = services.get_device_preview(preview_request)
		except DevicePreviewError as exc:
			raise HTTPException(status_code=_PREVIEW_STATUS_BY_KIND[exc.kind], detail=exc.kind.value) from exc
		headers = {**_PREVIEW_CACHE_CONTROL, "ETag": preview.etag}
		header = request.headers.get("if-none-match")
		if header and preview.etag in {token.strip() for token in header.split(",")}:
			return Response(status_code=304, headers=headers)
		return Response(content=preview.jpeg, media_type="image/jpeg", headers=headers)

	@router.get("/api/device/thumb")
	def device_thumb(
		request: Request,
		method: str,
		device_id: str,
		path: str,
		size: int = Query(ge=0),
		mtime: int = Query(ge=0),
	) -> Response:
		"""320 px JPEG of one phone photo (read-only; desktop-only)."""
		return serve_preview(request, DevicePreviewKind.THUMB, method, device_id, path, size, mtime)

	@router.get("/api/device/preview")
	def device_preview(
		request: Request,
		method: str,
		device_id: str,
		path: str,
		size: int = Query(ge=0),
		mtime: int = Query(ge=0),
	) -> Response:
		"""1600 px JPEG of one phone photo for the lightbox (read-only; desktop-only)."""
		return serve_preview(request, DevicePreviewKind.PREVIEW, method, device_id, path, size, mtime)

	return router
