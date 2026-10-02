from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.adapters.inbound.web.media_paths import _attachment_named
from spacemaker.adapters.inbound.web.models import ShareSelectionBody, TransferAddBody, TransferSaveBody
from spacemaker.adapters.inbound.web.qr_svg import qr_svg_response
from spacemaker.application.file_share_manifest import EmptyShareSelectionError
from spacemaker.application.transfer_session import EmptyTransferFolderError
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.transfer_session import TransferOrigin
from spacemaker.domain.upload_paths import is_safe_upload_relative_path


def build_lan_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.post("/api/share/selection")
	def share_selection(request: Request, body: ShareSelectionBody) -> dict[str, object]:
		require_loopback(request)
		try:
			services.set_share_selection(body.paths)
		except EmptyShareSelectionError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc
		return services.enriched_snapshot()

	@router.post("/api/transfer/add")
	def transfer_add(request: Request, body: TransferAddBody) -> dict[str, object]:
		require_loopback(request)
		try:
			services.add_transfer_paths_from_desktop(body.paths)
		except EmptyTransferFolderError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc
		except PermissionError as exc:
			raise HTTPException(status_code=403, detail=str(exc)) from exc
		return services.enriched_snapshot()

	@router.post("/api/transfer/save")
	def transfer_save(request: Request, body: TransferSaveBody) -> dict[str, str]:
		require_loopback(request)
		try:
			return services.save_transfer_item_to_documents(body.file_id)
		except ValueError as exc:
			raise HTTPException(status_code=400, detail=str(exc)) from exc
		except PermissionError as exc:
			raise HTTPException(status_code=403, detail=str(exc)) from exc
		except FileNotFoundError as exc:
			raise HTTPException(status_code=404, detail=str(exc)) from exc

	@router.get("/api/receive/qr.svg")
	def receive_qr(request: Request, t: str = "") -> Response:
		require_loopback(request)
		if not services.receive_token_valid(t):
			raise HTTPException(status_code=404, detail="receive session not active")
		page_url = services._receive_files_snapshot()["page_url"]
		if not page_url:
			raise HTTPException(status_code=404, detail="receive session not active")
		return qr_svg_response(str(page_url))

	@router.get("/api/share/qr.svg")
	def share_qr(request: Request, t: str = "") -> Response:
		require_loopback(request)
		if not services.share_token_valid(t):
			raise HTTPException(status_code=404, detail="share session not active")
		page_url = services._file_share_snapshot()["page_url"]
		if not page_url:
			raise HTTPException(status_code=404, detail="share session not active")
		return qr_svg_response(str(page_url))

	@router.get("/api/transfer/qr.svg")
	def transfer_qr(request: Request, t: str = "") -> Response:
		require_loopback(request)
		if not services.transfer_token_valid(t):
			raise HTTPException(status_code=404, detail="transfer session not active")
		page_url = services._transfer_files_snapshot()["page_url"]
		if not page_url:
			raise HTTPException(status_code=404, detail="transfer session not active")
		return qr_svg_response(str(page_url))

	@router.get("/api/receive/session")
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

	@router.post("/api/receive")
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

	@router.get("/api/share/session")
	def share_session_status(t: str = "") -> dict[str, object]:
		if not services.share_token_valid(t):
			return {"active": False, "files": []}
		return {"active": True, "files": services.share_manifest(t)}

	@router.get("/api/share/download")
	def share_download(
		background: BackgroundTasks,
		t: str = "",
		file_id: str = "",
	) -> FileResponse:
		if not file_id:
			raise HTTPException(status_code=400, detail="file_id required")
		target = services.resolve_share_download(t, file_id)
		if target is None:
			raise HTTPException(status_code=404, detail="file not found")
		if target.kind == "file":
			return FileResponse(
				target.source_path,
				headers={"Content-Disposition": _attachment_named(target.download_filename)},
			)
		zip_path = services.materialize_share_folder_zip(target.source_path)
		background.add_task(zip_path.unlink, missing_ok=True)
		return FileResponse(
			zip_path,
			media_type="application/zip",
			headers={"Content-Disposition": _attachment_named(target.download_filename)},
		)

	@router.get("/api/transfer/session")
	def transfer_session_status(t: str = "") -> dict[str, object]:
		if not services.transfer_token_valid(t):
			return {"active": False, "files": []}
		return {"active": True, "files": services.transfer_manifest(t)}

	@router.get("/api/transfer/download")
	def transfer_download(t: str = "", file_id: str = "") -> FileResponse:
		if not file_id:
			raise HTTPException(status_code=400, detail="file_id required")
		item = services.resolve_transfer_download(t, file_id)
		if item is None:
			raise HTTPException(status_code=404, detail="file not found")
		if item.kind.value == "folder_zip":
			return FileResponse(
				item.staged_path,
				media_type="application/zip",
				headers={"Content-Disposition": _attachment_named(item.display_name)},
			)
		return FileResponse(
			item.staged_path,
			headers={"Content-Disposition": _attachment_named(item.display_name)},
		)

	@router.post("/api/transfer")
	async def transfer_upload(
		files: Annotated[list[UploadFile], File()],
		t: Annotated[str, Query()] = "",
		as_folder: Annotated[str, Form()] = "",
		folder_name: Annotated[str, Form()] = "",
	) -> dict[str, object]:
		if not services.transfer_token_valid(t):
			raise HTTPException(status_code=403, detail="transfer session ended")
		if not files:
			raise HTTPException(status_code=400, detail="no files")
		folder_mode = as_folder.strip() in {"1", "true", "yes"} and bool(folder_name.strip())
		results: list[dict[str, str]] = []
		if folder_mode:
			relative_files: list[tuple[str, str]] = []
			temps: list[str] = []
			try:
				for upload in files:
					raw_name = upload.filename or "upload.bin"
					suffix = Path(raw_name).suffix
					with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
						temp_path = tmp.name
						temps.append(temp_path)
						while True:
							chunk = await upload.read(1024 * 1024)
							if not chunk:
								break
							tmp.write(chunk)
					rel = raw_name.replace("\\", "/")
					parts = Path(rel).parts
					if len(parts) > 1 and parts[0] == folder_name.strip():
						rel = "/".join(parts[1:])
					if not is_safe_upload_relative_path(rel):
						raise HTTPException(status_code=400, detail="invalid folder path")
					relative_files.append((rel, temp_path))
				item = services.handle_transfer_upload_folder_files(
					t,
					folder_name=folder_name.strip(),
					relative_files=relative_files,
					origin=TransferOrigin.PHONE,
				)
				temps = []
				if item is not None:
					results.append({"id": item.file_id, "name": item.display_name})
			except EmptyTransferFolderError as exc:
				raise HTTPException(status_code=400, detail=str(exc)) from exc
			except PermissionError as exc:
				raise HTTPException(status_code=403, detail=str(exc)) from exc
			finally:
				for path in temps:
					Path(path).unlink(missing_ok=True)
			return {"uploaded": len(results), "files": results}

		for upload in files:
			raw_name = upload.filename or "upload.bin"
			display = Path(raw_name.replace("\\", "/")).name or "upload.bin"
			suffix = Path(display).suffix
			temp_path: str | None = None
			try:
				with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
					temp_path = tmp.name
					while True:
						chunk = await upload.read(1024 * 1024)
						if not chunk:
							break
						tmp.write(chunk)
				item = services.handle_transfer_upload_file(
					t,
					requested_name=display,
					temp_path=temp_path,
					origin=TransferOrigin.PHONE,
				)
				temp_path = None
				if item is not None:
					results.append({"id": item.file_id, "name": item.display_name})
			except PermissionError as exc:
				raise HTTPException(status_code=403, detail=str(exc)) from exc
			finally:
				if temp_path is not None:
					Path(temp_path).unlink(missing_ok=True)
		return {"uploaded": len(results), "files": results}

	return router
