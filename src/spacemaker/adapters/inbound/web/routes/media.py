from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from spacemaker.adapters.inbound.web.media_paths import (
	_attachment_filename,
	_path_is_under_base,
	_resolve_processed_file,
)
from spacemaker.bootstrap.services import AppServices
from spacemaker.bootstrap.ui_shell import MEDIA_CACHE_HEADERS, THUMB_CACHE_HEADERS, file_etag
from spacemaker.domain.library import LibraryFolder


logger = logging.getLogger(__name__)


def _if_none_match_etags(request: Request) -> set[str]:
	"""Parse a comma-separated ``If-None-Match`` request header into its quoted ETag values."""
	header = request.headers.get("if-none-match")
	if not header:
		return set()
	return {token.strip() for token in header.split(",")}


def build_media_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.get("/thumbs/{relative_path:path}")
	def thumb_file(relative_path: str, request: Request) -> Response:
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
		except (OSError, RuntimeError) as exc:
			logger.warning("GET /thumbs/%s failed: %s", relative_path, exc)
			raise HTTPException(status_code=503, detail="thumbnail generation failed") from exc
		etag = file_etag(Path(thumb_path).stat())
		if etag in _if_none_match_etags(request):
			return Response(status_code=304, headers={**THUMB_CACHE_HEADERS, "ETag": etag})
		headers = {**THUMB_CACHE_HEADERS, "ETag": etag}
		return FileResponse(thumb_path, media_type="image/jpeg", headers=headers)

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
