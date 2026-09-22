import pytest
from fastapi.testclient import TestClient

from spacemaker.bootstrap.services import create_app


pytestmark = pytest.mark.integration


def test_given_fresh_app_when_get_index_then_returns_html() -> None:
	client = TestClient(create_app())
	response = client.get("/")
	assert response.status_code == 200
	assert "text/html" in response.headers.get("content-type", "")
	assert "SpaceMaker" in response.text


def test_given_fresh_app_when_get_settings_then_defaults() -> None:
	client = TestClient(create_app())
	response = client.get("/api/settings")
	assert response.status_code == 200
	body = response.json()
	assert body["connection_method"] == "mtp"
	assert body["extract"]["phase"] == "idle"
	assert body["library_root"]
	assert body["extract_controls"]["pause"] is False
	assert body["extract_controls"]["stop"] is False


def test_given_fresh_app_when_websocket_connects_then_receives_state() -> None:
	client = TestClient(create_app())
	with client.websocket_connect("/ws") as ws:
		message = ws.receive_json()
		assert message["type"] == "state"
		assert message["state"]["connection_method"] == "mtp"


def test_given_adb_without_bundled_tool_when_list_devices_then_503_json(monkeypatch, tmp_path) -> None:
	tools = tmp_path / "tools"
	tools.mkdir()
	monkeypatch.setenv("SPACEMAKER_DEV", "")
	monkeypatch.setattr(
		"spacemaker.adapters.outbound.media.tool_runner.bundle_root",
		lambda exe_dir=None: tools,
	)
	client = TestClient(create_app())
	response = client.get("/api/devices", params={"connection_method": "adb"})
	assert response.status_code == 503
	body = response.json()
	assert "detail" in body
	assert "adb" in body["detail"].lower()


def test_given_originals_on_disk_when_convert_start_then_running(tmp_path) -> None:
	library = tmp_path / "lib"
	originals = library / "originals"
	originals.mkdir(parents=True)
	(originals / "a.jpg").write_bytes(b"fake")

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(originals),
			"connection_method": "mtp",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": ["dcim"],
		},
	)
	response = client.post("/api/convert/start")
	assert response.status_code == 200
	body = response.json()
	assert body["convert"]["phase"] in {"running", "done"}
