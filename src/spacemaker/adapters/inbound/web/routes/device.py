from __future__ import annotations

import sys

from fastapi import APIRouter, HTTPException, Request

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

	return router
