from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from spacemaker.adapters.inbound.web.client_access import is_loopback_client_host, require_loopback
from spacemaker.adapters.inbound.web.media_paths import (
	_attachment_filename,
	_content_disposition,
	_resolve_processed_file,
	_session_library_root,
)
from spacemaker.adapters.inbound.web.models import GalleryExportBody, GalleryOpenBody
from spacemaker.adapters.inbound.web.serializers import _gallery_item_dict, _metadata_dict
from spacemaker.adapters.outbound.host.open_paths import open_file_with_default_app, reveal_in_file_manager
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.gallery_export import ExportFormat, ExportJobPhase, is_safe_gallery_relative_path


def build_gallery_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.get("/api/gallery/timeline")
	async def gallery_timeline(cursor: str | None = None, limit: int = 150) -> dict[str, object]:
		root = _session_library_root(services)
		if not root:
			return {"items": [], "next_cursor": None}
		bounded_limit = max(1, min(limit, 500))
		if cursor is None:
			await services.sync_gallery_index.run(root)
		try:
			page = await services.gallery.list_timeline_page(root, cursor=cursor, limit=bounded_limit)
		except ValueError as exc:
			raise HTTPException(status_code=400, detail="invalid cursor") from exc
		return {
			"items": [_gallery_item_dict(item) for item in page.items],
			"next_cursor": page.next_cursor,
		}

	@router.get("/api/gallery/calendar")
	async def gallery_calendar(year: int, month: int) -> dict[str, object]:
		root = _session_library_root(services)
		if not root:
			return {"year": year, "month": month, "days_with_media": []}
		await services.sync_gallery_index.run(root)
		days = await services.gallery.calendar_days(root, year, month)
		return {"year": year, "month": month, "days_with_media": days}

	@router.get("/api/gallery/item")
	async def gallery_item_detail(request: Request, path: str) -> dict[str, object]:
		root = _session_library_root(services)
		if not root:
			raise HTTPException(status_code=404, detail="library not configured")
		if not is_safe_gallery_relative_path(path):
			raise HTTPException(status_code=403, detail="invalid path")
		indexed = await services.gallery_index.get(root, path)
		detail = services.get_gallery_item.get(
			root,
			path,
			indexed=indexed,
		)
		if detail is None:
			raise HTTPException(status_code=404, detail="not found")
		return {
			"relative_path": detail.item.relative_path,
			# The host filesystem path is only meaningful (and only disclosed) to the desktop app.
			"absolute_path": detail.absolute_path
			if is_loopback_client_host(request.client.host if request.client else None)
			else "",
			"captured_at": detail.item.captured_at.isoformat(),
			"kind": detail.item.kind.value,
			"preview_in_browser": detail.preview_in_browser,
			"metadata": _metadata_dict(detail.metadata),
		}

	@router.delete("/api/gallery/item")
	async def gallery_item_delete(path: str) -> dict[str, object]:
		root = _session_library_root(services)
		if not root:
			raise HTTPException(status_code=400, detail="library not configured")
		if not is_safe_gallery_relative_path(path):
			raise HTTPException(status_code=403, detail="invalid path")
		try:
			removed = await services.remove_gallery_item(root, path)
		except ValueError as exc:
			raise HTTPException(status_code=403, detail=str(exc)) from exc
		if not removed:
			raise HTTPException(status_code=404, detail="not found")
		return {"deleted": True, "relative_path": path}

	@router.post("/api/gallery/open")
	def gallery_open_on_host(request: Request, body: GalleryOpenBody) -> dict[str, bool]:
		require_loopback(request)
		target = _resolve_processed_file(services, body.relative_path)
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

	@router.post("/api/gallery/export")
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
		_resolve_processed_file(services, body.relative_path)
		job = services.start_gallery_export(root, body.relative_path, export_format)
		return job.to_dict()

	@router.get("/api/gallery/export/{job_id}")
	def gallery_export_status(job_id: str) -> dict[str, object]:
		# HTTP status poll: LAN phones cannot use the loopback-only /ws push.
		job = services.get_export_job(job_id)
		if job is None:
			raise HTTPException(status_code=404, detail="unknown job")
		return job.to_dict()

	@router.get("/api/gallery/export/{job_id}/file")
	def gallery_export_file(job_id: str, inline: int = 0) -> FileResponse:
		job = services.get_export_job(job_id)
		if job is None:
			raise HTTPException(status_code=404, detail="unknown job")
		if job.phase is not ExportJobPhase.DONE:
			raise HTTPException(status_code=409, detail="export not ready")
		path = Path(job.download_path)
		if not path.is_file():
			raise HTTPException(status_code=404, detail="export file missing")
		if inline:
			disposition = _content_disposition("inline", path.name)
		else:
			disposition = _attachment_filename(path)
		return FileResponse(path, headers={"Content-Disposition": disposition})

	@router.get("/api/gallery/day")
	async def gallery_day(year: int, month: int, day: int) -> dict[str, object]:
		root = _session_library_root(services)
		if not root:
			return {"year": year, "month": month, "day": day, "items": []}
		items = await services.gallery.list_day(root, year, month, day)
		return {
			"year": year,
			"month": month,
			"day": day,
			"items": [_gallery_item_dict(item) for item in items],
		}

	@router.get("/api/gallery/item/neighbor")
	async def gallery_item_neighbor(path: str, direction: str) -> dict[str, object]:
		root = _session_library_root(services)
		if not root:
			raise HTTPException(status_code=404, detail="library not configured")
		if not is_safe_gallery_relative_path(path):
			raise HTTPException(status_code=403, detail="invalid path")
		if direction not in ("prev", "next"):
			raise HTTPException(status_code=400, detail="invalid direction")
		found = await services.gallery.neighbor(root, path, direction=direction)
		return {"relative_path": found.relative_path if found is not None else None}

	return router
