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


def test_given_converted_files_when_get_settings_then_visualize_ready(tmp_path) -> None:
	library = tmp_path / "lib"
	converted = library / "converted"
	converted.mkdir(parents=True)
	(converted / "photo.avif").write_bytes(b"x")

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"connection_method": "mtp",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": ["dcim"],
		},
	)
	response = client.get("/api/settings")
	body = response.json()
	assert body["visualize"]["enabled"] is True
	assert "1" in body["visualize"]["status_text"]


def test_given_gallery_route_when_get_then_html_200() -> None:
	client = TestClient(create_app())
	response = client.get("/gallery")
	assert response.status_code == 200


def test_given_app_when_get_qr_svg_then_svg() -> None:
	client = TestClient(create_app())
	response = client.get("/api/gallery/qr.svg")
	assert response.status_code == 200
	assert "svg" in response.headers.get("content-type", "")


def test_given_gallery_item_route_when_get_then_html_200() -> None:
	client = TestClient(create_app())
	response = client.get("/gallery/item/photo.avif")
	assert response.status_code == 200
	assert "text/html" in response.headers.get("content-type", "")


def test_given_converted_file_when_gallery_item_api_then_metadata(tmp_path) -> None:
	library = tmp_path / "lib"
	converted = library / "converted"
	converted.mkdir(parents=True)
	(converted / "photo.avif").write_bytes(b"x")

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"connection_method": "mtp",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": ["dcim"],
		},
	)
	response = client.get("/api/gallery/item", params={"path": "photo.avif"})
	assert response.status_code == 200
	body = response.json()
	assert body["relative_path"] == "photo.avif"
	assert body["metadata"]["filename"] == "photo.avif"


def test_given_media_download_flag_when_get_then_attachment(tmp_path) -> None:
	library = tmp_path / "lib"
	converted = library / "converted"
	converted.mkdir(parents=True)
	(converted / "photo.avif").write_bytes(b"x")

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"connection_method": "mtp",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": ["dcim"],
		},
	)
	response = client.get("/media/photo.avif", params={"download": 1})
	assert response.status_code == 200
	assert "attachment" in response.headers.get("content-disposition", "")


def test_given_converted_fixture_when_calendar_then_days(tmp_path) -> None:
	library = tmp_path / "lib"
	converted = library / "converted"
	converted.mkdir(parents=True)
	(converted / "a.avif").write_bytes(b"x")

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"connection_method": "mtp",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": ["dcim"],
		},
	)
	response = client.get("/api/gallery/calendar", params={"year": 1970, "month": 1})
	assert response.status_code == 200
	body = response.json()
	assert body["year"] == 1970
	assert isinstance(body["days_with_media"], list)
