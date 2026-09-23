from __future__ import annotations

from ipaddress import ip_address

from fastapi import HTTPException, Request
from starlette.websockets import WebSocket


def is_loopback_client_host(host: str | None) -> bool:
	if not host:
		return False
	if host in {"localhost", "127.0.0.1", "::1"}:
		return True
	# Starlette TestClient ASGI peer name (not used by real HTTP clients).
	if host == "testclient":
		return True
	try:
		return ip_address(host).is_loopback
	except ValueError:
		return False


def require_loopback(request: Request) -> None:
	client = request.client
	if client is None or not is_loopback_client_host(client.host):
		raise HTTPException(status_code=403, detail="desktop-only")


def require_loopback_websocket(websocket: WebSocket) -> bool:
	client = websocket.client
	if client is None or not is_loopback_client_host(client.host):
		return False
	return True
