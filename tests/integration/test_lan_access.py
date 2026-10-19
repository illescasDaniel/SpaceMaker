from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import WebSocketRoute
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from tests.unit.passcode_fakes import FakeClock, FakePasscodeCrypto, FakePasscodeStore

from spacemaker.adapters.inbound.web.lan_policy import is_lan_allowed
from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.bootstrap.services import create_app


pytestmark = pytest.mark.integration


def _lan(app: FastAPI, host: str = "10.0.0.2") -> TestClient:
	async def lan_app(scope, receive, send):  # type: ignore[no-untyped-def]
		scope = dict(scope)
		if scope["type"] in {"http", "websocket"}:
			scope["client"] = (host, 43210)
		await app(scope, receive, send)

	return TestClient(lan_app)


def _routes(app: FastAPI) -> list[tuple[str, str]]:
	found: list[tuple[str, str]] = []

	def walk(routes: list, prefix: str = "") -> None:  # type: ignore[type-arg]
		for route in routes:
			original = getattr(route, "original_router", None)
			if original is not None:
				walk(original.routes, prefix)
			elif isinstance(route, APIRoute):
				found.extend((method, prefix + route.path) for method in route.methods if method != "HEAD")
			elif isinstance(route, WebSocketRoute):
				found.append(("WS", route.path))

	walk(app.routes)
	return found


def _concrete(path: str) -> str:
	return path.replace("{relative_path:path}", "a/b.jpg").replace("{job_id}", "job1").replace("{doc_id}", "privacy")


def test_given_lan_client_when_get_root_then_notice_page_not_the_app() -> None:
	# given
	client = _lan(create_app())
	# when
	response = client.get("/", headers={"Host": "localhost:8765"})
	# then
	assert response.status_code == 200
	assert "controlled from the computer" in response.text
	assert 'href="/gallery"' in response.text
	assert "btn-extract" not in response.text


def test_given_lan_client_spoofing_localhost_host_when_gallery_then_mobile_shell() -> None:
	# given
	client = _lan(create_app())
	# when
	response = client.get("/gallery", headers={"Host": "localhost"})
	# then
	assert response.status_code == 200
	assert 'SPACEMAKER_SHELL = "mobile_gallery"' in response.text


@pytest.mark.parametrize(
	("method", "path"),
	[
		("GET", "/api/server-info"),
		("GET", "/api/gallery/qr.svg"),
		("GET", "/api/legal/privacy"),
		("GET", "/json/version"),
		("GET", "/json/list"),
		("PUT", "/api/settings"),
		("POST", "/api/gallery/open"),
		("GET", "/docs"),
	],
)
def test_given_lan_client_when_control_api_then_403_desktop_only(method: str, path: str) -> None:
	# given
	client = _lan(create_app())
	# when
	response = client.request(method, path)
	# then
	assert response.status_code == 403
	assert response.json() == {"detail": "desktop-only"}


def test_given_loopback_client_when_control_api_then_not_blocked() -> None:
	# given
	client = TestClient(create_app())
	# when
	response = client.get("/api/server-info")
	# then
	assert response.status_code == 200
	assert client.get("/").status_code == 200


def test_given_lan_client_when_gallery_timeline_then_allowed() -> None:
	# given
	client = _lan(create_app())
	# when
	response = client.get("/api/gallery/timeline")
	# then
	assert response.status_code != 403


def test_given_passcode_and_lan_client_when_control_api_then_401_before_403() -> None:
	# given
	app = create_app()
	passcode = NetworkPasscode(FakePasscodeStore(), FakePasscodeCrypto(), FakeClock())
	passcode.load()
	passcode.set_passcode("123456")
	app.state.services.network_passcode = passcode
	client = _lan(app)
	# when
	response = client.get("/api/server-info")
	# then
	assert response.status_code == 401


def test_given_lan_client_when_websocket_then_refused() -> None:
	# given
	client = _lan(create_app())
	# when / then
	with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws") as ws:
		ws.receive_text()


def test_given_every_registered_route_when_lan_client_then_allowed_or_403() -> None:
	# given
	app = create_app()
	client = _lan(app)
	routes = [(m, p) for m, p in _routes(app) if m != "WS"]
	assert len(routes) > 50
	# when / then
	for method, template in routes:
		path = _concrete(template)
		if path == "/":
			continue
		response = client.request(method, path)
		if is_lan_allowed(method, path):
			assert response.status_code != 403 or response.json().get("detail") != "desktop-only", (method, path)
		else:
			assert response.status_code == 403, (method, path)
			assert response.json() == {"detail": "desktop-only"}, (method, path)
