from __future__ import annotations

from fastapi import APIRouter, Request

from spacemaker.adapters.inbound.web.client_access import require_loopback
from spacemaker.bootstrap.services import AppServices


def build_tools_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.get("/api/tools/status")
	def tools_status(request: Request) -> dict[str, object]:
		require_loopback(request)
		return services.managed_tools.status_dict()

	@router.post("/api/tools/ensure")
	def tools_ensure(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.managed_tools.ensure_all()
		return services.managed_tools.status_dict()

	@router.post("/api/tools/components-continue")
	def tools_components_continue(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.managed_tools.allow_path_fallback()
		return services.managed_tools.status_dict()

	@router.delete("/api/tools/downloaded")
	def tools_delete_downloaded(request: Request) -> dict[str, object]:
		require_loopback(request)
		services.managed_tools.delete_downloaded()
		return services.managed_tools.status_dict()

	return router
