from __future__ import annotations

from fastapi import Request

from spacemaker.bootstrap.services import AppServices


# Prefer build_*_router(services) factories that close over AppServices.
# Use get_services only when a handler needs Depends(Request)-style injection.


def get_services(request: Request) -> AppServices:
	return request.app.state.services
