from pathlib import Path

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
	csp = response.headers.get("content-security-policy", "")
	assert "unsafe-eval" in csp


def test_given_devtools_probe_when_get_json_version_then_200() -> None:
	client = TestClient(create_app())
	response = client.get("/json/version")
	assert response.status_code == 200
	assert response.json().get("Protocol-Version") == "1.3"


def test_given_fresh_app_when_get_settings_then_defaults() -> None:
	client = TestClient(create_app())
	response = client.get("/api/settings")
	assert response.status_code == 200
	body = response.json()
	assert body["connection_method"] == "wifi"
	assert body["ui_mode"] == "easy"
	assert body["extract"]["phase"] == "idle"
	assert body["library_root"]
	assert body["extract_controls"]["pause"] is False
	assert body["extract_controls"]["stop"] is False
	assert "managed_tools" in body
	assert "tools_dir" in body["managed_tools"]
	assert "compress_media" in body
	assert set(body["compress_media"]) >= {"enabled", "control_enabled", "tools_available"}


def test_given_tools_available_when_put_compress_media_off_then_persists(monkeypatch) -> None:
	# given
	client = TestClient(create_app())
	monkeypatch.setattr(
		client.app.state.services.compression_tools,
		"available",
		lambda: True,
	)

	# when
	response = client.put("/api/settings", json={"compress_media": False, "library_root": ""})

	# then
	assert response.status_code == 200
	assert response.json()["compress_media"]["enabled"] is False
	assert response.json()["compress_media"]["control_enabled"] is True
	again = client.get("/api/settings").json()["compress_media"]
	assert again["enabled"] is False


def test_given_tools_unavailable_when_put_compress_media_on_then_stays_off(monkeypatch) -> None:
	# given
	client = TestClient(create_app())
	monkeypatch.setattr(
		client.app.state.services.compression_tools,
		"available",
		lambda: False,
	)

	# when
	response = client.put("/api/settings", json={"compress_media": True, "library_root": ""})

	# then
	body = response.json()["compress_media"]
	assert body["enabled"] is False
	assert body["control_enabled"] is False
	assert body["tools_available"] is False


def test_given_fresh_app_when_get_tools_status_then_lists_tools() -> None:
	client = TestClient(create_app())
	response = client.get("/api/tools/status")
	assert response.status_code == 200
	body = response.json()
	assert body["tools_dir"]
	assert isinstance(body["tools"], list)
	from spacemaker.bootstrap.bundled_tools import BundledTool

	assert len(body["tools"]) == len(BundledTool)


def test_given_fresh_app_when_websocket_connects_then_receives_state() -> None:
	client = TestClient(create_app())
	with client.websocket_connect("/ws") as ws:
		message = ws.receive_json()
		assert message["type"] == "state"
		assert message["state"]["connection_method"] == "wifi"


def test_given_adb_without_bundled_tool_when_list_devices_then_503_json(monkeypatch, tmp_path) -> None:
	tools = tmp_path / "tools"
	tools.mkdir()
	monkeypatch.setenv("SPACEMAKER_TOOLS_DIR", str(tools))
	monkeypatch.setattr(
		"spacemaker.bootstrap.bundled_tools.shutil.which",
		lambda _name: None,
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
	body = response.text
	assert 'fill="#fff"' in body or 'fill="#ffffff"' in body


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
	assert Path(body["absolute_path"]).resolve() == (converted / "photo.avif").resolve()


def test_given_converted_file_when_open_on_host_then_ok(tmp_path, monkeypatch) -> None:
	library = tmp_path / "lib"
	converted = library / "converted"
	converted.mkdir(parents=True)
	(converted / "photo.avif").write_bytes(b"x")
	opened: list[str] = []
	monkeypatch.setattr(
		"spacemaker.adapters.inbound.web.app.open_file_with_default_app",
		lambda path: opened.append(path),
	)

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
	response = client.post(
		"/api/gallery/open",
		json={"relative_path": "photo.avif", "target": "file"},
	)
	assert response.status_code == 200
	assert opened and opened[0].endswith("photo.avif")


def test_given_converted_file_when_delete_item_then_removed(tmp_path) -> None:
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
	response = client.delete("/api/gallery/item", params={"path": "photo.avif"})
	assert response.status_code == 200
	assert response.json()["deleted"] is True
	assert not (converted / "photo.avif").is_file()


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


def test_given_wifi_extract_when_upload_then_file_in_originals(tmp_path) -> None:
	library = tmp_path / "lib"
	library.mkdir()

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"ui_mode": "advanced",
			"connection_method": "wifi",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": [],
		},
	)
	start = client.post("/api/extract/start")
	assert start.status_code == 200
	body = start.json()
	assert body["wifi_upload"]["active"] is True
	token = body["wifi_upload"]["upload_url"].split("t=")[1]

	upload = client.post(
		"/api/upload",
		params={"t": token},
		files=[("files", ("photo.jpg", b"hello", "image/jpeg"))],
	)
	assert upload.status_code == 200
	assert (library / "originals" / "photo.jpg").is_file()

	stop = client.post("/api/extract/stop")
	assert stop.status_code == 200
	ended = client.post(
		"/api/upload",
		params={"t": token},
		files=[("files", ("other.jpg", b"x", "image/jpeg"))],
	)
	assert ended.status_code == 403


def test_given_wifi_extract_running_with_originals_when_convert_start_then_stops_extract(tmp_path) -> None:
	library = tmp_path / "lib"
	originals = library / "originals"
	originals.mkdir(parents=True)
	(originals / "already.jpg").write_bytes(b"x")

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"connection_method": "wifi",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": [],
		},
	)
	client.post("/api/extract/start")
	assert client.get("/api/settings").json()["extract"]["phase"] == "running"

	response = client.post("/api/convert/start")
	assert response.status_code == 200
	body = response.json()
	assert body["extract"]["phase"] == "stopped"
	assert body["convert"]["phase"] in {"running", "done"}
	assert body["wifi_upload"]["active"] is False


def test_given_easy_mode_when_first_upload_then_wifi_session_stays_active(tmp_path) -> None:
	library = tmp_path / "lib"
	library.mkdir()

	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"ui_mode": "easy",
			"connection_method": "wifi",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": [],
		},
	)
	bootstrap = client.post("/api/easy/bootstrap")
	assert bootstrap.status_code == 200
	body = bootstrap.json()
	assert body["wifi_upload"]["active"] is True
	token = body["wifi_upload"]["upload_url"].split("t=")[1]

	upload = client.post(
		"/api/upload",
		params={"t": token},
		files=[("files", ("photo.jpg", b"hello", "image/jpeg"))],
	)
	assert upload.status_code == 200
	assert (library / "originals" / "photo.jpg").is_file()

	after = client.get("/api/settings").json()
	assert after["extract"]["phase"] == "running"
	assert after["wifi_upload"]["active"] is True
	assert after["wifi_upload"]["upload_url"].split("t=")[1] == token

	session = client.get("/api/upload/session", params={"t": token}).json()
	assert session["accepts_uploads"] is True
	assert session["active"] is True


def test_given_easy_bootstrap_when_post_then_wifi_extract_running(tmp_path) -> None:
	library = tmp_path / "lib"
	library.mkdir()
	client = TestClient(create_app())
	client.put(
		"/api/settings",
		json={
			"library_root": str(library),
			"ui_mode": "easy",
			"connection_method": "wifi",
			"transfer_mode": "copy",
			"device_id": "",
			"source_folders": [],
		},
	)
	response = client.post("/api/easy/bootstrap")
	assert response.status_code == 200
	body = response.json()
	assert body["ui_mode"] == "easy"
	assert body["extract"]["phase"] == "running"
	assert body["wifi_upload"]["active"] is True


def test_given_lan_host_when_get_gallery_then_mobile_shell() -> None:
	client = TestClient(create_app())
	response = client.get("/gallery", headers={"Host": "192.168.0.5:8765"})
	assert response.status_code == 200
	assert 'SPACEMAKER_SHELL = "mobile_gallery"' in response.text
	assert "btn-ui-easy" not in response.text


def test_given_lan_host_when_get_root_then_mobile_remote_landing() -> None:
	client = TestClient(create_app())
	response = client.get("/", headers={"Host": "192.168.0.5:8765"})
	assert response.status_code == 200
	assert "Use the QR codes on your PC" in response.text
