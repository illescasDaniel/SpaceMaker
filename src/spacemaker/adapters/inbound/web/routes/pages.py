from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from spacemaker.adapters.inbound.web.media_paths import (
	_STATIC,
	_no_cache_file,
	_stamped_shell_page,
)
from spacemaker.adapters.inbound.web.spa_entry import SpaEntry, normalize_host, spa_entry_for
from spacemaker.bootstrap.services import AppServices


def build_pages_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	def _spa_file(entry: SpaEntry) -> Path:
		if entry is SpaEntry.DESKTOP:
			return _STATIC / "index.html"
		if entry is SpaEntry.MOBILE_GALLERY:
			return _STATIC / "gallery_mobile.html"
		return _STATIC / "mobile_remote.html"

	def _spa_response(entry: SpaEntry) -> Response:
		path = _spa_file(entry)
		if entry is SpaEntry.DESKTOP or entry is SpaEntry.MOBILE_GALLERY:
			return _stamped_shell_page(path)
		return _no_cache_file(path)

	@router.get("/json/version")
	def devtools_version_probe() -> dict[str, str]:
		# Qt WebEngine / Chromium poll this for remote debugging; stub avoids 404 log noise.
		return {"Browser": "SpaceMaker", "Protocol-Version": "1.3"}

	@router.get("/json/list")
	def devtools_list_probe() -> list[dict[str, object]]:
		return []

	@router.get("/")
	def root_page(request: Request) -> Response:
		host = normalize_host(request.headers.get("host", ""))
		entry = spa_entry_for(host=host, path="/")
		return _spa_response(entry)

	@router.get("/gallery")
	@router.get("/gallery/item/{relative_path:path}")
	def gallery_page(request: Request, relative_path: str = "") -> Response:
		_ = relative_path
		host = normalize_host(request.headers.get("host", ""))
		entry = spa_entry_for(host=host, path=request.url.path)
		return _spa_response(entry)

	@router.get("/upload")
	def upload_page(t: str = "") -> FileResponse:
		if not services.wifi_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "upload.html")

	@router.get("/upload/ended")
	def upload_ended_page() -> FileResponse:
		return FileResponse(_STATIC / "upload-ended.html")

	@router.get("/receive")
	def receive_page(t: str = "") -> FileResponse:
		if not services.receive_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "receive.html")

	@router.get("/share")
	def share_page(t: str = "") -> FileResponse:
		if not services.share_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "share.html")

	@router.get("/transfer")
	def transfer_page(t: str = "") -> FileResponse:
		if not services.transfer_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "transfer.html")

	@router.get("/favicon.ico")
	def favicon() -> FileResponse:
		icon = _STATIC / "favicon.png"
		if not icon.is_file():
			raise HTTPException(status_code=404)
		return FileResponse(icon, media_type="image/png")

	return router
