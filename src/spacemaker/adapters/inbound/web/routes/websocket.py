from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from spacemaker.adapters.inbound.web.client_access import require_loopback_websocket
from spacemaker.bootstrap.services import AppServices


def build_websocket_router(services: AppServices) -> APIRouter:
	router = APIRouter()

	@router.websocket("/ws")
	async def websocket_endpoint(websocket: WebSocket) -> None:
		if not require_loopback_websocket(websocket):
			await websocket.close(code=1008, reason="desktop-only")
			return
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

	return router
