from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import segno
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from spacemaker.bootstrap.firewall import probe_gallery_port
from spacemaker.bootstrap.lan import lan_ip
from spacemaker.bootstrap.paths import (
	default_library_root,
	is_absolute_library_path,
	normalize_library_root,
	pictures_directory,
)
from spacemaker.bootstrap.services import AppServices, repo_root
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.jobs import JobPhase, can_start_convert
from spacemaker.domain.library import LibraryFolder, TransferMode


def _gallery_item_dict(item: GalleryItem) -> dict[str, str]:
	return {
		"relative_path": item.relative_path,
		"captured_at": item.captured_at.isoformat(),
		"kind": item.kind.value,
	}


_STATIC = Path(__file__).resolve().parent / "static"
_LEGAL = {
	"privacy": repo_root() / "docs" / "legal" / "PRIVACY.md",
	"disclaimer": repo_root() / "docs" / "legal" / "DISCLAIMER.md",
	"third_party": repo_root() / "docs" / "legal" / "THIRD_PARTY_TOOLS.md",
}


class SettingsBody(BaseModel):
	library_root: str = ""
	connection_method: ConnectionMethod = ConnectionMethod.MTP
	transfer_mode: TransferMode = TransferMode.COPY
	device_id: str = ""
	device_label: str = ""
	source_folders: list[str] | None = None


def create_fastapi_app(services: AppServices) -> FastAPI:
	app = FastAPI(title="SpaceMaker", version="0.1.0")
	app.mount("/static", StaticFiles(directory=_STATIC), name="static")

	@app.get("/")
	@app.get("/gallery")
	def index() -> FileResponse:
		return FileResponse(_STATIC / "index.html")

	@app.get("/api/server-info")
	def server_info() -> dict[str, object]:
		host = lan_ip()
		gallery_url = f"http://{host}:{services.port}/gallery"
		lan_listening = services.bind_host in {"0.0.0.0", "::"}  # noqa: S104
		firewall = probe_gallery_port(services.port, bind_host=services.bind_host)
		return {
			"host": host,
			"port": services.port,
			"gallery_url": gallery_url,
			"qr_url": "/api/gallery/qr.svg",
			"lan_listening": lan_listening,
			"lan_reachable": lan_listening and host != "127.0.0.1",
			"firewall": {
				"backend": firewall.backend,
				"active": firewall.active,
				"port_open": firewall.port_open,
				"lan_connect_ok": firewall.lan_connect_ok,
				"message": firewall.message,
			},
		}

	@app.get("/api/gallery/qr.svg")
	def gallery_qr() -> Response:
		gallery_url = f"http://{lan_ip()}:{services.port}/gallery"
		buffer = BytesIO()
		segno.make(gallery_url).save(buffer, kind="svg", scale=8)
		return Response(content=buffer.getvalue(), media_type="image/svg+xml")

	@app.get("/api/defaults")
	def defaults() -> dict[str, str]:
		root = default_library_root()
		return {
			"default_library_root": root,
			"pictures_directory": str(pictures_directory()),
		}

	@app.get("/api/settings")
	def get_settings() -> dict[str, object]:
		return services.enriched_snapshot()

	@app.put("/api/settings")
	def put_settings(body: SettingsBody) -> dict[str, object]:
		with services.session._lock:
			if services.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				raise HTTPException(status_code=409, detail="cannot change settings during extract")
			library_root = normalize_library_root(body.library_root)
			if library_root and not is_absolute_library_path(library_root):
				raise HTTPException(status_code=400, detail="library_root must be an absolute path")
			previous_method = services.session.connection_method
			services.session.library_root = library_root
			services.session.connection_method = body.connection_method
			services.session.transfer_mode = body.transfer_mode
			if body.connection_method is not previous_method:
				services.session.device_id = ""
				services.session.device_label = ""
			device_id = body.device_id.strip()
			repo = services.devices_for(body.connection_method)
			known = {d.device_id: d.label for d in repo.list_devices()}
			if device_id and device_id in known:
				services.session.device_id = device_id
				services.session.device_label = known[device_id]
			else:
				services.session.device_id = ""
				services.session.device_label = ""
			if body.source_folders is not None:
				services.session.source_folders = [f.lower() for f in body.source_folders]
			if services.session.library_root:
				services.filesystem.ensure_library_folders(services.session.library_root)
		services.push_state()
		return services.enriched_snapshot()

	@app.get("/api/devices")
	def list_devices(connection_method: ConnectionMethod = ConnectionMethod.MTP) -> list[dict[str, str]]:
		try:
			repo = services.devices_for(connection_method)
			devices = repo.list_devices()
		except FileNotFoundError as exc:
			raise HTTPException(status_code=503, detail=str(exc)) from exc
		if services.reconcile_device_selection(connection_method):
			services.push_state()
		return [{"device_id": d.device_id, "label": d.label} for d in devices]

	@app.get("/api/library/counts")
	def library_counts(library_root: str = "") -> dict[str, int]:
		root = library_root or services.session.library_root
		return services.folder_counts(root)

	@app.post("/api/extract/start")
	def extract_start() -> dict[str, object]:
		if not services.session.library_root or not is_absolute_library_path(services.session.library_root):
			raise HTTPException(status_code=400, detail="choose a valid library folder")
		if not services.session.device_id:
			raise HTTPException(status_code=400, detail="select a device")
		if not services.session.source_folders:
			raise HTTPException(status_code=400, detail="select at least one source folder")
		services.start_extract()
		return services.enriched_snapshot()

	@app.post("/api/extract/pause")
	def extract_pause() -> dict[str, object]:
		services.pause_extract()
		return services.enriched_snapshot()

	@app.post("/api/extract/resume")
	def extract_resume() -> dict[str, object]:
		services.resume_extract()
		return services.enriched_snapshot()

	@app.post("/api/extract/stop")
	def extract_stop() -> dict[str, object]:
		services.stop_extract()
		return services.enriched_snapshot()

	@app.post("/api/convert/start")
	def convert_start() -> dict[str, object]:
		with services.session._lock:
			root = normalize_library_root(services.session.library_root)
			if root:
				services.session.library_root = root
		if not services.session.library_root:
			raise HTTPException(status_code=400, detail="library_root required")
		originals = services.filesystem.count_files_in_folder(
			services.session.library_root,
			LibraryFolder.ORIGINALS,
		)
		extract_phase = services.session.extract_phase
		if not can_start_convert(extract_phase=extract_phase, originals_count=originals):
			raise HTTPException(
				status_code=409,
				detail=(f"convert not available (extract={extract_phase.value}, originals={originals})"),
			)
		if services.session.convert_phase is JobPhase.RUNNING:
			raise HTTPException(status_code=409, detail="convert already running")
		services.start_convert()
		return services.enriched_snapshot()

	@app.post("/api/error/move-to-converted")
	def move_errors() -> dict[str, int]:
		if not services.session.library_root:
			raise HTTPException(status_code=400, detail="library_root required")
		moved = services.error_recovery.move_all_errors_to_converted(services.session.library_root)
		services.invalidate_gallery_metadata_cache()
		services.push_state()
		return {"moved": moved}

	@app.get("/api/gallery/timeline")
	def gallery_timeline(library_root: str = "") -> list[dict[str, object]]:
		root = library_root or services.session.library_root
		if not root:
			return []
		groups = services.gallery.list_timeline(root, captured_at_for=services.captured_at_map(root))
		return [
			{
				"year": group.year,
				"month": group.month,
				"items": [_gallery_item_dict(item) for item in group.items],
			}
			for group in groups
		]

	@app.get("/api/gallery/calendar")
	def gallery_calendar(year: int, month: int, library_root: str = "") -> dict[str, object]:
		root = library_root or services.session.library_root
		if not root:
			return {"year": year, "month": month, "days_with_media": []}
		days = services.gallery.calendar_days(
			root,
			year,
			month,
			captured_at_for=services.captured_at_map(root),
		)
		return {"year": year, "month": month, "days_with_media": days}

	@app.get("/api/gallery/day")
	def gallery_day(year: int, month: int, day: int, library_root: str = "") -> dict[str, object]:
		root = library_root or services.session.library_root
		if not root:
			return {"year": year, "month": month, "day": day, "items": []}
		items = services.gallery.list_day(
			root,
			year,
			month,
			day,
			captured_at_for=services.captured_at_map(root),
		)
		return {
			"year": year,
			"month": month,
			"day": day,
			"items": [_gallery_item_dict(item) for item in items],
		}

	@app.get("/thumbs/{relative_path:path}")
	def thumb_file(relative_path: str) -> FileResponse:
		root = services.session.library_root
		if not root:
			raise HTTPException(status_code=404)
		base = Path(services.filesystem.library_path(root, LibraryFolder.CONVERTED, "")).resolve()
		target = (base / relative_path).resolve()
		if not str(target).startswith(str(base)):
			raise HTTPException(status_code=403, detail="invalid path")
		if not target.is_file():
			raise HTTPException(status_code=404)
		try:
			thumb_path = services.thumbnails.ensure_thumb(root, relative_path)
		except FileNotFoundError as exc:
			raise HTTPException(status_code=404, detail=str(exc)) from exc
		except OSError as exc:
			raise HTTPException(status_code=500, detail="thumbnail generation failed") from exc
		return FileResponse(thumb_path, media_type="image/jpeg")

	@app.get("/api/legal/{doc_id}")
	def legal_doc(doc_id: str) -> dict[str, str]:
		path = _LEGAL.get(doc_id)
		if path is None or not path.is_file():
			raise HTTPException(status_code=404, detail="unknown legal document")
		return {"id": doc_id, "markdown": path.read_text(encoding="utf-8")}

	@app.get("/media/{relative_path:path}")
	def media_file(relative_path: str) -> FileResponse:
		root = services.session.library_root
		if not root:
			raise HTTPException(status_code=404)
		base = Path(services.filesystem.library_path(root, LibraryFolder.CONVERTED, "")).resolve()
		target = (base / relative_path).resolve()
		if not str(target).startswith(str(base)):
			raise HTTPException(status_code=403, detail="invalid path")
		if not target.is_file():
			raise HTTPException(status_code=404)
		return FileResponse(target)

	@app.websocket("/ws")
	async def websocket_endpoint(websocket: WebSocket) -> None:
		await websocket.accept()
		if services._event_loop is None:
			services.bind_event_loop(asyncio.get_running_loop())
		services.register_ws(websocket)
		await websocket.send_json({"type": "state", "state": services.enriched_snapshot()})
		try:
			while True:
				await websocket.receive_text()
		except WebSocketDisconnect:
			services.unregister_ws(websocket)

	return app
