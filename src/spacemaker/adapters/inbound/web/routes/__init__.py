from __future__ import annotations

from fastapi import FastAPI

from spacemaker.adapters.inbound.web.routes.convert import build_convert_router
from spacemaker.adapters.inbound.web.routes.extract import build_extract_router
from spacemaker.adapters.inbound.web.routes.gallery import build_gallery_router
from spacemaker.adapters.inbound.web.routes.lan import build_lan_router
from spacemaker.adapters.inbound.web.routes.media import build_media_router
from spacemaker.adapters.inbound.web.routes.pages import build_pages_router
from spacemaker.adapters.inbound.web.routes.settings import build_settings_router
from spacemaker.adapters.inbound.web.routes.tools import build_tools_router
from spacemaker.adapters.inbound.web.routes.usb_transfer import build_usb_transfer_router
from spacemaker.adapters.inbound.web.routes.websocket import build_websocket_router
from spacemaker.bootstrap.services import AppServices


def register_routes(app: FastAPI, services: AppServices) -> None:
	app.include_router(build_pages_router(services))
	app.include_router(build_settings_router(services))
	app.include_router(build_lan_router(services))
	app.include_router(build_extract_router(services))
	app.include_router(build_usb_transfer_router(services))
	app.include_router(build_convert_router(services))
	app.include_router(build_gallery_router(services))
	app.include_router(build_media_router(services))
	app.include_router(build_tools_router(services))
	app.include_router(build_websocket_router(services))
