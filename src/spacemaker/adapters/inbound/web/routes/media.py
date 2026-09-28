from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from spacemaker.adapters.inbound.web.media_paths import (
	_attachment_filename,
	_path_is_under_base,
	_resolve_processed_file,
)
from spacemaker.bootstrap.services import AppServices
from spacemaker.bootstrap.ui_shell import MEDIA_CACHE_HEADERS
from spacemaker.domain.library import LibraryFolder


def build_media_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.get("/thumbs/{relative_path:path}")
	def thumb_file(relative_path: str) -> FileResponse:
		root = services.session.library_root
		if not root:
			raise HTTPException(status_code=404)
		base = Path(services.filesystem.library_path(root, LibraryFolder.PROCESSED, "")).resolve()
		target = (base / relative_path).resolve()
		if not _path_is_under_base(base, target):
			raise HTTPException(status_code=403, detail="invalid path")
		if not target.is_file():
			raise HTTPException(status_code=404)
		try:
			thumb_path = services.thumbnails.ensure_thumb(root, relative_path)
		except FileNotFoundError as exc:
			raise HTTPException(status_code=404, detail=str(exc)) from exc
		except OSError as exc:
			raise HTTPException(status_code=500, detail="thumbnail generation failed") from exc
		return FileResponse(thumb_path, media_type="image/jpeg", headers=dict(MEDIA_CACHE_HEADERS))

	@router.get("/media/{relative_path:path}")
	def media_file(relative_path: str, download: int = 0) -> FileResponse:
		target = _resolve_processed_file(services, relative_path)
		headers: dict[str, str] = {}
		if download:
			headers["Content-Disposition"] = _attachment_filename(target)
		else:
			headers.update(MEDIA_CACHE_HEADERS)
		return FileResponse(target, headers=headers)

	return router
