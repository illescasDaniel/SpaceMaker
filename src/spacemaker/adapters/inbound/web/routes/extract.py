from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.adapters.inbound.web.media_paths import _session_library_root
from spacemaker.adapters.inbound.web.qr_svg import encode_qr_svg
from spacemaker.bootstrap.lan import lan_ip
from spacemaker.bootstrap.paths import is_absolute_library_path
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.connection import ConnectionMethod


def build_extract_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.get("/api/extract/upload-qr.svg")
	def extract_upload_qr(request: Request, t: str = "") -> Response:
		require_loopback(request)
		if not services.wifi_token_valid(t):
			raise HTTPException(status_code=404, detail="upload session not active")
		upload_url = f"http://{lan_ip()}:{services.port}/upload?t={t}"
		return Response(content=encode_qr_svg(upload_url), media_type="image/svg+xml")

	@router.get("/api/upload/session")
	def upload_session_status(t: str = "") -> dict[str, object]:
		if not services.wifi_token_valid(t):
			return {"active": False, "accepts_uploads": False, "phase": "ended", "files_sent": 0}
		with services.session._lock:
			phase = services.session.extract_phase.value
			files_sent = services.session.extract_progress.completed
		return {
			"active": True,
			"accepts_uploads": services.wifi_session_accepts_uploads(),
			"phase": phase,
			"files_sent": files_sent,
		}

	@router.post("/api/upload")
	async def upload_files(
		files: Annotated[list[UploadFile], File()],
		t: Annotated[str, Query()] = "",
	) -> dict[str, object]:
		if not services.wifi_token_valid(t):
			raise HTTPException(status_code=403, detail="upload session ended")
		if not services.wifi_session_accepts_uploads():
			raise HTTPException(status_code=409, detail="upload session paused or stopped")
		if not files:
			raise HTTPException(status_code=400, detail="no files")
		results: list[dict[str, str]] = []
		for upload in files:
			raw_name = upload.filename or "upload.bin"
			suffix = Path(raw_name).suffix
			with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
				temp_path = tmp.name
				size = 0
				while True:
					chunk = await upload.read(1024 * 1024)
					if not chunk:
						break
					tmp.write(chunk)
					size += len(chunk)
			try:
				services.handle_wifi_upload(t, raw_name, temp_path, size)
				results.append({"file": raw_name, "status": "ok"})
			except PermissionError as exc:
				services.filesystem.delete_file(temp_path)
				raise HTTPException(status_code=409, detail=str(exc)) from exc
			except ValueError as exc:
				services.filesystem.delete_file(temp_path)
				raise HTTPException(status_code=400, detail=str(exc)) from exc
			except Exception:
				services.filesystem.delete_file(temp_path)
				raise
		return {"uploaded": len(results), "files": results}

	@router.get("/api/devices")
	def list_devices(
		request: Request,
		connection_method: ConnectionMethod = ConnectionMethod.WIFI,
	) -> list[dict[str, str]]:
		require_loopback(request)
		if connection_method is ConnectionMethod.WIFI:
			return []
		if connection_method is ConnectionMethod.AFC and sys.platform != "linux":
			raise HTTPException(
				status_code=501,
				detail="iPhone (USB) extract is only available on Linux in this release",
			)
		try:
			repo = services.devices_for(connection_method)
			devices = repo.list_devices()
		except FileNotFoundError as exc:
			raise HTTPException(status_code=503, detail=str(exc)) from exc
		except RuntimeError as exc:
			raise HTTPException(status_code=503, detail=str(exc)) from exc
		if services.reconcile_device_selection(connection_method):
			services.push_state()
		return [{"device_id": d.device_id, "label": d.label} for d in devices]

	@router.get("/api/library/counts")
	def library_counts(request: Request) -> dict[str, int]:
		require_loopback(request)
		root = _session_library_root(services)
		return services.folder_counts(root)

	@router.post("/api/extract/start")
	def extract_start(request: Request) -> dict[str, object]:
		require_loopback(request)
		if not services.session.library_root or not is_absolute_library_path(services.session.library_root):
			raise HTTPException(status_code=400, detail="choose a valid library folder")
		method = services.session.connection_method
		if method is ConnectionMethod.WIFI:
			services.start_extract()
			return services.enriched_snapshot()
		if not services.session.device_id:
			raise HTTPException(status_code=400, detail="select a device")
		if not services.session.source_folders:
			raise HTTPException(status_code=400, detail="select at least one source folder")
		services.start_extract()
		return services.enriched_snapshot()

	@router.post("/api/extract/pause")
	def extract_pause(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.pause_extract()
		return services.enriched_snapshot()

	@router.post("/api/extract/resume")
	def extract_resume(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.resume_extract()
		return services.enriched_snapshot()

	@router.post("/api/extract/stop")
	def extract_stop(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.stop_extract_and_wait(timeout_seconds=300.0)
		return services.enriched_snapshot()

	return router
