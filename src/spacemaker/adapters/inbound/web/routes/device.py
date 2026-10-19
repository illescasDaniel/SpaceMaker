from __future__ import annotations

import sys

from fastapi import APIRouter, HTTPException

from spacemaker.adapters.inbound.web.models import DeviceListBody
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseError, DeviceBrowseErrorKind


_STATUS_BY_KIND: dict[DeviceBrowseErrorKind, int] = {
	DeviceBrowseErrorKind.INVALID_PATH: 400,
	DeviceBrowseErrorKind.NOT_FOUND: 404,
	DeviceBrowseErrorKind.PERMISSION_DENIED: 403,
	DeviceBrowseErrorKind.UNAUTHORIZED: 403,
	DeviceBrowseErrorKind.UNPLUGGED: 409,
	DeviceBrowseErrorKind.TIMEOUT: 504,
	DeviceBrowseErrorKind.FAILED: 502,
}


def build_device_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.post("/api/device/list")
	def device_list(body: DeviceListBody) -> dict[str, object]:
		"""List one phone directory for the in-app picker (read-only; passcode-gated, not loopback-only)."""
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
		try:
			page = services.list_device_directory(method, body.device_id, body.path, max(0, body.cursor))
		except DeviceBrowseError as exc:
			status = _STATUS_BY_KIND[exc.kind]
			raise HTTPException(status_code=status, detail={"error": exc.kind.value, "message": exc.detail}) from exc
		return {
			"path": page.path,
			"entries": [{"name": e.name, "is_dir": e.is_dir, "size": e.size, "mtime": e.mtime} for e in page.entries],
			"next_cursor": page.next_cursor,
			"total": page.total,
		}

	return router
