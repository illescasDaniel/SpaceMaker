from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.bootstrap.paths import normalize_library_root
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.convert_policy import ConvertStartPolicy
from spacemaker.domain.jobs import can_start_convert
from spacemaker.domain.library import LibraryFolder


def build_convert_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.post("/api/convert/start")
	def convert_start(request: Request) -> dict[str, object]:
		require_loopback(request)
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
			originals_count=originals,
			convert_job_active=services._convert_job_active(),
		):
			raise HTTPException(
				status_code=409,
				detail=f"convert not available (originals={originals})",
			)
		if services._convert_job_active():
			raise HTTPException(status_code=409, detail="convert already running")
		services.start_convert(policy=ConvertStartPolicy.STOP_EXTRACT_FIRST)
		return services.enriched_snapshot()

	@router.post("/api/convert/stop")
	def convert_stop(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.stop_convert_and_wait(timeout_seconds=300.0)
		return services.enriched_snapshot()

	@router.post("/api/error/move-to-processed")
	async def move_errors(request: Request) -> dict[str, int]:
		require_loopback(request)
		if not services.session.library_root:
			raise HTTPException(status_code=400, detail="library_root required")
		moved = services.error_recovery.move_all_errors_to_processed(services.session.library_root)
		await services.sync_gallery_index.run(services.session.library_root)
		services.push_state()
		return {"moved": moved}

	return router
