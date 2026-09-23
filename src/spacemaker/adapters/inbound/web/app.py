from __future__ import annotations

import asyncio
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Annotated

import segno
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from spacemaker.adapters.inbound.web.spa_entry import SpaEntry, normalize_host, spa_entry_for
from spacemaker.adapters.outbound.host.open_paths import open_file_with_default_app, reveal_in_file_manager
from spacemaker.bootstrap.firewall import probe_gallery_port
from spacemaker.bootstrap.lan import lan_ip
from spacemaker.bootstrap.paths import (
	default_documents_receive_root,
	default_library_root,
	documents_directory,
	documents_folder_open_target,
	is_absolute_library_path,
	normalize_library_root,
	pictures_directory,
)
from spacemaker.bootstrap.services import AppServices, repo_root
from spacemaker.bootstrap.ui_shell import NO_CACHE_HEADERS
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.convert_policy import ConvertStartPolicy
from spacemaker.domain.gallery import GalleryItem
from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase, is_safe_gallery_relative_path
from spacemaker.domain.gallery_metadata import GalleryDisplayMetadata
from spacemaker.domain.jobs import JobPhase, can_start_convert
from spacemaker.domain.library import LibraryFolder, TransferMode
from spacemaker.domain.ui_mode import UiMode


def _gallery_item_dict(item: GalleryItem) -> dict[str, str]:
	return {
		"relative_path": item.relative_path,
		"captured_at": item.captured_at.isoformat(),
		"kind": item.kind.value,
	}


def _metadata_dict(meta: GalleryDisplayMetadata) -> dict[str, object]:
	return {
		"filename": meta.filename,
		"captured_at": meta.captured_at.isoformat() if meta.captured_at else None,
		"camera_make": meta.camera_make,
		"camera_model": meta.camera_model,
		"width": meta.width,
		"height": meta.height,
		"duration_seconds": meta.duration_seconds,
		"file_size_bytes": meta.file_size_bytes,
		"gps": meta.gps,
	}


def _resolve_converted_file(services: AppServices, relative_path: str) -> Path:
	if not is_safe_gallery_relative_path(relative_path):
		raise HTTPException(status_code=403, detail="invalid path")
	root = services.session.library_root
	if not root:
		raise HTTPException(status_code=404)
	base = Path(services.filesystem.library_path(root, LibraryFolder.CONVERTED, "")).resolve()
	target = (base / relative_path).resolve()
	if not str(target).startswith(str(base)):
		raise HTTPException(status_code=403, detail="invalid path")
	if not target.is_file():
		raise HTTPException(status_code=404)
	return target


def _attachment_filename(path: Path) -> str:
	name = path.name.replace('"', "")
	return f'attachment; filename="{name}"'


class GalleryExportBody(BaseModel):
	relative_path: str
	format: str


class GalleryOpenBody(BaseModel):
	relative_path: str
	target: str


_STATIC = Path(__file__).resolve().parent / "static"
_LEGAL = {
	"privacy": repo_root() / "docs" / "legal" / "PRIVACY.md",
	"disclaimer": repo_root() / "docs" / "legal" / "DISCLAIMER.md",
	"third_party": repo_root() / "docs" / "legal" / "THIRD_PARTY_TOOLS.md",
}


class ModuleEnterBody(BaseModel):
	module: AppModule


class ShareSelectionBody(BaseModel):
	paths: list[str]


class LibraryOpenFolderBody(BaseModel):
	bucket: str


class SettingsBody(BaseModel):
	library_root: str = ""
	ui_mode: UiMode | None = None
	connection_method: ConnectionMethod = ConnectionMethod.WIFI
	transfer_mode: TransferMode = TransferMode.COPY
	device_id: str = ""
	device_label: str = ""
	source_folders: list[str] | None = None


def _no_cache_file(path: Path) -> FileResponse:
	return FileResponse(path, headers=dict(NO_CACHE_HEADERS))


def create_fastapi_app(services: AppServices) -> FastAPI:
	app = FastAPI(title="SpaceMaker", version="0.1.0")
	app.mount("/static", StaticFiles(directory=_STATIC), name="static")

	@app.middleware("http")
	async def no_cache_shell_assets(request: Request, call_next):
		response = await call_next(request)
		path = request.url.path
		if path == "/" or path.startswith("/gallery") or path == "/static/app.js":
			for key, value in NO_CACHE_HEADERS.items():
				response.headers[key] = value
		return response

	def _spa_file(entry: SpaEntry) -> Path:
		if entry is SpaEntry.DESKTOP:
			return _STATIC / "index.html"
		if entry is SpaEntry.MOBILE_GALLERY:
			return _STATIC / "gallery_mobile.html"
		return _STATIC / "mobile_remote.html"

	@app.get("/json/version")
	def devtools_version_probe() -> dict[str, str]:
		# Qt WebEngine / Chromium poll this for remote debugging; stub avoids 404 log noise.
		return {"Browser": "SpaceMaker", "Protocol-Version": "1.3"}

	@app.get("/json/list")
	def devtools_list_probe() -> list[dict[str, object]]:
		return []

	@app.get("/")
	def root_page(request: Request) -> FileResponse:
		host = normalize_host(request.headers.get("host", ""))
		entry = spa_entry_for(host=host, path="/")
		return _no_cache_file(_spa_file(entry))

	@app.get("/gallery")
	@app.get("/gallery/item/{relative_path:path}")
	def gallery_page(request: Request, relative_path: str = "") -> FileResponse:
		_ = relative_path
		host = normalize_host(request.headers.get("host", ""))
		entry = spa_entry_for(host=host, path=request.url.path)
		return _no_cache_file(_spa_file(entry))

	@app.get("/upload")
	def upload_page(t: str = "") -> FileResponse:
		if not services.wifi_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "upload.html")

	@app.get("/upload/ended")
	def upload_ended_page() -> FileResponse:
		return FileResponse(_STATIC / "upload-ended.html")

	@app.get("/receive")
	def receive_page(t: str = "") -> FileResponse:
		if not services.receive_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "receive.html")

	@app.get("/share")
	def share_page(t: str = "") -> FileResponse:
		if not services.share_token_valid(t):
			return FileResponse(_STATIC / "upload-ended.html")
		return FileResponse(_STATIC / "share.html")

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
			"documents_receive_root": default_documents_receive_root(),
		}

	@app.get("/api/settings")
	def get_settings() -> dict[str, object]:
		return services.enriched_snapshot()

	@app.put("/api/settings")
	def put_settings(body: SettingsBody) -> dict[str, object]:
		with services.session._lock:
			if body.ui_mode is not None:
				services.session.ui_mode = body.ui_mode
			if services.session.extract_phase in {JobPhase.RUNNING, JobPhase.PAUSED}:
				services.push_state()
				return services.enriched_snapshot()
			library_root = normalize_library_root(body.library_root)
			if library_root and not is_absolute_library_path(library_root):
				raise HTTPException(status_code=400, detail="library_root must be an absolute path")
			previous_method = services.session.connection_method
			services.session.library_root = library_root
			services.session.connection_method = body.connection_method
			if body.connection_method is ConnectionMethod.WIFI:
				services.session.transfer_mode = TransferMode.COPY
			else:
				services.session.transfer_mode = body.transfer_mode
			if body.connection_method is not previous_method:
				services.session.device_id = ""
				services.session.device_label = ""
			device_id = body.device_id.strip()
			if body.connection_method is ConnectionMethod.WIFI:
				services.session.device_id = ""
				services.session.device_label = ""
			else:
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

	@app.post("/api/easy/bootstrap")
	def easy_bootstrap() -> dict[str, object]:
		if not services.session.library_root or not is_absolute_library_path(services.session.library_root):
			raise HTTPException(status_code=400, detail="choose a valid library folder")
		services.ensure_easy_session()
		return services.enriched_snapshot()

	@app.post("/api/module/enter")
	def module_enter(body: ModuleEnterBody) -> dict[str, object]:
		if body.module in {AppModule.PHOTO_BACKUP, AppModule.USB_PHOTO_BACKUP}:
			if not services.session.library_root or not is_absolute_library_path(services.session.library_root):
				raise HTTPException(status_code=400, detail="choose a valid library folder")
		services.enter_module(body.module)
		return services.enriched_snapshot()

	@app.post("/api/module/home")
	def module_home() -> dict[str, object]:
		services.leave_module_for_home()
		return services.enriched_snapshot()

	@app.post("/api/share/selection")
	def share_selection(body: ShareSelectionBody) -> dict[str, object]:
		services.set_share_selection(body.paths)
		return services.enriched_snapshot()

	@app.get("/api/receive/qr.svg")
	def receive_qr(t: str = "") -> Response:
		if not services.receive_token_valid(t):
			raise HTTPException(status_code=404, detail="receive session not active")
		page_url = services._receive_files_snapshot()["page_url"]
		if not page_url:
			raise HTTPException(status_code=404, detail="receive session not active")
		buffer = BytesIO()
		segno.make(str(page_url)).save(buffer, kind="svg", scale=8)
		return Response(content=buffer.getvalue(), media_type="image/svg+xml")

	@app.get("/api/share/qr.svg")
	def share_qr(t: str = "") -> Response:
		if not services.share_token_valid(t):
			raise HTTPException(status_code=404, detail="share session not active")
		page_url = services._file_share_snapshot()["page_url"]
		if not page_url:
			raise HTTPException(status_code=404, detail="share session not active")
		buffer = BytesIO()
		segno.make(str(page_url)).save(buffer, kind="svg", scale=8)
		return Response(content=buffer.getvalue(), media_type="image/svg+xml")

	@app.get("/api/receive/session")
	def receive_session_status(t: str = "") -> dict[str, object]:
		if not services.receive_token_valid(t):
			return {"active": False, "accepts_uploads": False, "phase": "ended", "files_sent": 0}
		with services.session._lock:
			phase = services.session.receive_files_phase.value
			files_sent = services.session.receive_files_progress.completed
		return {
			"active": True,
			"accepts_uploads": services.receive_session_accepts_uploads(),
			"phase": phase,
			"files_sent": files_sent,
		}

	@app.post("/api/receive")
	async def receive_files_upload(
		files: Annotated[list[UploadFile], File()],
		t: Annotated[str, Query()] = "",
	) -> dict[str, object]:
		if not services.receive_token_valid(t):
			raise HTTPException(status_code=403, detail="receive session ended")
		if not services.receive_session_accepts_uploads():
			raise HTTPException(status_code=409, detail="receive session paused or stopped")
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
				services.handle_receive_upload(t, raw_name, temp_path, size)
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

	@app.get("/api/share/session")
	def share_session_status(t: str = "") -> dict[str, object]:
		if not services.share_token_valid(t):
			return {"active": False, "files": []}
		return {"active": True, "files": services.share_manifest(t)}

	@app.get("/api/share/download")
	def share_download(t: str = "", file_id: str = "") -> FileResponse:
		if not file_id:
			raise HTTPException(status_code=400, detail="file_id required")
		target = services.shared_file_for_download(t, file_id)
		if target is None:
			raise HTTPException(status_code=404, detail="file not found")
		return FileResponse(target, headers={"Content-Disposition": _attachment_filename(target)})

	@app.post("/api/documents/open-folder")
	def open_documents_folder() -> dict[str, bool]:
		primary = documents_folder_open_target()
		fallback = documents_directory()
		try:
			reveal_in_file_manager(str(primary))
		except (OSError, FileNotFoundError):
			if primary.resolve() == fallback.resolve():
				raise HTTPException(status_code=500, detail="Could not open Documents folder") from None
			try:
				reveal_in_file_manager(str(fallback))
			except (OSError, FileNotFoundError) as exc:
				raise HTTPException(status_code=500, detail=str(exc)) from exc
		return {"ok": True}

	@app.post("/api/library/open-folder")
	def open_library_folder(body: LibraryOpenFolderBody) -> dict[str, bool]:
		bucket = body.bucket.strip().lower()
		if bucket not in {"error", "invalid"}:
			raise HTTPException(status_code=400, detail="unknown bucket")
		root = services.session.library_root
		if not root or not is_absolute_library_path(root):
			raise HTTPException(status_code=400, detail="library not configured")
		folder = LibraryFolder.ERROR if bucket == "error" else LibraryFolder.INVALID
		target = Path(services.filesystem.library_path(root, folder, ""))
		target.mkdir(parents=True, exist_ok=True)
		try:
			reveal_in_file_manager(str(target))
		except OSError as exc:
			raise HTTPException(status_code=500, detail=str(exc)) from exc
		return {"ok": True}

	@app.get("/api/extract/upload-qr.svg")
	def extract_upload_qr(t: str = "") -> Response:
		if not services.wifi_token_valid(t):
			raise HTTPException(status_code=404, detail="upload session not active")
		upload_url = f"http://{lan_ip()}:{services.port}/upload?t={t}"
		buffer = BytesIO()
		segno.make(upload_url).save(buffer, kind="svg", scale=8)
		return Response(content=buffer.getvalue(), media_type="image/svg+xml")

	@app.get("/api/upload/session")
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

	@app.post("/api/upload")
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

	@app.get("/api/devices")
	def list_devices(connection_method: ConnectionMethod = ConnectionMethod.WIFI) -> list[dict[str, str]]:
		if connection_method is ConnectionMethod.WIFI:
			return []
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
		if not can_start_convert(
			extract_phase=services.session.extract_phase,
			originals_count=originals,
		):
			raise HTTPException(
				status_code=409,
				detail=f"convert not available (originals={originals})",
			)
		if services.session.convert_phase is JobPhase.RUNNING:
			raise HTTPException(status_code=409, detail="convert already running")
		services.start_convert(policy=ConvertStartPolicy.STOP_EXTRACT_FIRST)
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

	@app.get("/api/gallery/item")
	def gallery_item_detail(path: str, library_root: str = "") -> dict[str, object]:
		root = library_root or services.session.library_root
		if not root:
			raise HTTPException(status_code=404, detail="library not configured")
		if not is_safe_gallery_relative_path(path):
			raise HTTPException(status_code=403, detail="invalid path")
		captured_map = services.captured_at_map(root)
		detail = services.get_gallery_item.get(
			root,
			path,
			captured_at=captured_map.get(path),
		)
		if detail is None:
			raise HTTPException(status_code=404, detail="not found")
		return {
			"relative_path": detail.item.relative_path,
			"absolute_path": detail.absolute_path,
			"captured_at": detail.item.captured_at.isoformat(),
			"kind": detail.item.kind.value,
			"preview_in_browser": detail.preview_in_browser,
			"metadata": _metadata_dict(detail.metadata),
		}

	@app.delete("/api/gallery/item")
	def gallery_item_delete(path: str, library_root: str = "") -> dict[str, object]:
		root = library_root or services.session.library_root
		if not root:
			raise HTTPException(status_code=400, detail="library not configured")
		if not is_safe_gallery_relative_path(path):
			raise HTTPException(status_code=403, detail="invalid path")
		try:
			removed = services.remove_gallery_item(root, path)
		except ValueError as exc:
			raise HTTPException(status_code=403, detail=str(exc)) from exc
		if not removed:
			raise HTTPException(status_code=404, detail="not found")
		return {"deleted": True, "relative_path": path}

	@app.post("/api/gallery/open")
	def gallery_open_on_host(body: GalleryOpenBody) -> dict[str, bool]:
		target = _resolve_converted_file(services, body.relative_path)
		try:
			if body.target == "file":
				open_file_with_default_app(str(target))
			elif body.target == "folder":
				reveal_in_file_manager(str(target))
			else:
				raise HTTPException(status_code=400, detail="unknown target")
		except FileNotFoundError as exc:
			raise HTTPException(status_code=404, detail=str(exc)) from exc
		except OSError as exc:
			raise HTTPException(status_code=500, detail=str(exc)) from exc
		return {"ok": True}

	@app.post("/api/gallery/export")
	def gallery_export_start(body: GalleryExportBody) -> dict[str, object]:
		root = services.session.library_root
		if not root:
			raise HTTPException(status_code=400, detail="library not configured")
		if not is_safe_gallery_relative_path(body.relative_path):
			raise HTTPException(status_code=403, detail="invalid path")
		try:
			export_format = ExportFormat(body.format)
		except ValueError as exc:
			raise HTTPException(status_code=400, detail="unknown export format") from exc
		_resolve_converted_file(services, body.relative_path)
		job = services.start_gallery_export(root, body.relative_path, export_format)
		return job.to_dict()

	@app.get("/api/gallery/export/{job_id}/file")
	def gallery_export_file(job_id: str, inline: int = 0) -> FileResponse:
		job = services.get_export_job(job_id)
		if job is None:
			raise HTTPException(status_code=404, detail="unknown job")
		if job.phase is not ExportJobPhase.DONE:
			raise HTTPException(status_code=409, detail="export not ready")
		path = Path(job.download_path)
		if not path.is_file():
			raise HTTPException(status_code=404, detail="export file missing")
		name = path.name.replace('"', "")
		if inline:
			disposition = f'inline; filename="{name}"'
		else:
			disposition = _attachment_filename(path)
		return FileResponse(path, headers={"Content-Disposition": disposition})

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

	@app.get("/favicon.ico")
	def favicon() -> FileResponse:
		icon = _STATIC / "favicon.png"
		if not icon.is_file():
			raise HTTPException(status_code=404)
		return FileResponse(icon, media_type="image/png")

	@app.get("/api/tools/status")
	def tools_status() -> dict[str, object]:
		return services.managed_tools.status_dict()

	@app.post("/api/tools/ensure")
	def tools_ensure() -> dict[str, object]:
		services.managed_tools.ensure_all()
		return services.managed_tools.status_dict()

	@app.post("/api/tools/components-continue")
	def tools_components_continue() -> dict[str, object]:
		services.managed_tools.allow_path_fallback()
		return services.managed_tools.status_dict()

	@app.delete("/api/tools/downloaded")
	def tools_delete_downloaded() -> dict[str, object]:
		services.managed_tools.delete_downloaded()
		return services.managed_tools.status_dict()

	@app.get("/api/legal/{doc_id}")
	def legal_doc(doc_id: str) -> dict[str, str]:
		path = _LEGAL.get(doc_id)
		if path is None or not path.is_file():
			raise HTTPException(status_code=404, detail="unknown legal document")
		return {"id": doc_id, "markdown": path.read_text(encoding="utf-8")}

	@app.get("/media/{relative_path:path}")
	def media_file(relative_path: str, download: int = 0) -> FileResponse:
		target = _resolve_converted_file(services, relative_path)
		headers: dict[str, str] | None = None
		if download:
			headers = {"Content-Disposition": _attachment_filename(target)}
		return FileResponse(target, headers=headers)

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
