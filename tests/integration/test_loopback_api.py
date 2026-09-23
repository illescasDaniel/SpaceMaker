from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from spacemaker.bootstrap.services import create_app


pytestmark = pytest.mark.integration


def _lan_client_app():
	base = create_app()

	async def lan_app(scope, receive, send):
		scope = dict(scope)
		if scope["type"] in {"http", "websocket"}:
			scope["client"] = ("10.0.0.2", 43210)
		await base(scope, receive, send)

	return lan_app


def test_given_lan_client_when_get_settings_then_403() -> None:
	client = TestClient(_lan_client_app())
	response = client.get("/api/settings")
	assert response.status_code == 403
	assert response.json()["detail"] == "desktop-only"


def test_given_lan_client_when_put_settings_then_403() -> None:
	client = TestClient(_lan_client_app())
	response = client.put(
		"/api/settings",
		json={"library_root": "/var/lib/spacemaker-test", "connection_method": "wifi"},
	)
	assert response.status_code == 403


def test_given_lan_client_when_gallery_timeline_then_200_if_session_has_library() -> None:
	client = TestClient(_lan_client_app())
	response = client.get("/api/gallery/timeline")
	assert response.status_code == 200
