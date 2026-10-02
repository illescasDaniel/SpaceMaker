from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from spacemaker import __version__ as app_version
from spacemaker.adapters.inbound.web.client_access import is_loopback_client_host
from spacemaker.adapters.inbound.web.media_paths import _STATIC
from spacemaker.adapters.inbound.web.passcode_guard import passcode_challenge
from spacemaker.adapters.inbound.web.routes import register_routes
from spacemaker.bootstrap.services import AppServices
from spacemaker.bootstrap.ui_shell import (
	CONTENT_SECURITY_POLICY,
	CONTENT_SECURITY_POLICY_DESKTOP,
	NO_CACHE_HEADERS,
)


def create_fastapi_app(services: AppServices) -> FastAPI:
	@asynccontextmanager
	async def lifespan(app: FastAPI) -> AsyncIterator[None]:
		_ = app
		yield
		services.shutdown()

	app = FastAPI(title="SpaceMaker", version=app_version, lifespan=lifespan)
	app.state.services = services
	app.mount("/static", StaticFiles(directory=_STATIC), name="static")

	# Registered first = innermost, so the unlock page still passes through the shell
	# middleware below and gets the same CSP / no-store headers as the pages it replaces.
	@app.middleware("http")
	async def network_passcode_guard(
		request: Request,
		call_next: Callable[[Request], Awaitable[Response]],
	) -> Response:
		challenge = passcode_challenge(request, services.network_passcode)
		if challenge is not None:
			return challenge
		return await call_next(request)

	@app.middleware("http")
	async def no_cache_shell_assets(
		request: Request,
		call_next: Callable[[Request], Awaitable[Response]],
	) -> Response:
		response = await call_next(request)
		path = request.url.path
		# Local desktop shell must always see current CSS/JS — never a stale WebEngine cache.
		if path == "/" or path.startswith("/gallery") or path.startswith("/static/"):
			for key, value in NO_CACHE_HEADERS.items():
				response.headers[key] = value
		if path == "/" or path.startswith("/gallery") or path in {"/upload", "/receive", "/share", "/transfer"}:
			client_host = request.client.host if request.client else None
			if is_loopback_client_host(client_host):
				response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY_DESKTOP
			else:
				response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
		return response

	register_routes(app, services)
	return app
