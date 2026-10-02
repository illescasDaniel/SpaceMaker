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


def test_given_unknown_export_job_when_poll_status_then_404(tmp_path, monkeypatch) -> None:
	# given
	monkeypatch.setenv("HOME", str(tmp_path))
	client = TestClient(create_app())
	# when
	response = client.get("/api/gallery/export/nope")
	# then
	assert response.status_code == 404


def _library_with_photo(tmp_path, monkeypatch):
	monkeypatch.setenv("HOME", str(tmp_path))
	app = create_app()
	library = tmp_path / "lib"
	(library / "processed").mkdir(parents=True)
	(library / "processed" / "a.jpg").write_bytes(b"\xff\xd8\xff\xd9")
	app.state.services.session.library_root = str(library)
	return app


def test_given_lan_client_when_gallery_item_then_host_path_is_not_disclosed(tmp_path, monkeypatch) -> None:
	# given
	app = _library_with_photo(tmp_path, monkeypatch)

	async def lan_app(scope, receive, send):
		scope = dict(scope)
		scope["client"] = ("10.0.0.2", 43210)
		await app(scope, receive, send)

	# when
	response = TestClient(lan_app).get("/api/gallery/item", params={"path": "a.jpg"})
	# then
	assert response.status_code == 200
	assert response.json()["absolute_path"] == ""


def test_given_desktop_client_when_gallery_item_then_host_path_is_returned(tmp_path, monkeypatch) -> None:
	# given
	app = _library_with_photo(tmp_path, monkeypatch)
	# when
	response = TestClient(app).get("/api/gallery/item", params={"path": "a.jpg"})
	# then
	assert response.status_code == 200
	assert response.json()["absolute_path"].endswith("a.jpg")


@pytest.mark.parametrize("evil_name", ["/etc/cron.d/x", "C:/Windows/x.txt", "pics/../../x.txt"])
def test_given_transfer_folder_upload_with_unsafe_path_when_post_then_400(tmp_path, monkeypatch, evil_name) -> None:
	# given
	from spacemaker.domain.app_module import AppModule

	monkeypatch.setenv("HOME", str(tmp_path))
	app = create_app()
	services = app.state.services
	services.enter_module(AppModule.TRANSFER_FILES)
	token = services._transfer_session_token
	client = TestClient(app)
	# when
	response = client.post(
		f"/api/transfer?t={token}",
		data={"as_folder": "1", "folder_name": "pics"},
		files=[("files", (evil_name, b"data", "text/plain"))],
	)
	# then
	assert response.status_code == 400
	services.shutdown()


def _wait_for_export(client: TestClient, job_id: str) -> dict[str, object]:
	import time

	deadline = time.monotonic() + 10
	while time.monotonic() < deadline:
		job = client.get(f"/api/gallery/export/{job_id}").json()
		if job["phase"] != "running":
			return job
		time.sleep(0.05)
	raise AssertionError("export never finished")


def test_given_lan_client_when_export_then_poll_reaches_done_and_exposes_no_host_path(tmp_path, monkeypatch) -> None:
	# given
	app = _library_with_photo(tmp_path, monkeypatch)

	async def lan_app(scope, receive, send):
		scope = dict(scope)
		scope["client"] = ("10.0.0.2", 43210)
		await app(scope, receive, send)

	client = TestClient(lan_app)
	# when
	started = client.post("/api/gallery/export", json={"relative_path": "a.jpg", "format": "jpeg"})
	job = _wait_for_export(client, started.json()["job_id"])
	file_response = client.get(job["download_url"])
	# then
	assert started.status_code == 200
	assert job["phase"] == "done"
	assert str(tmp_path) not in started.text
	assert str(tmp_path) not in str(job)
	assert file_response.status_code == 200
	assert str(tmp_path) not in str(file_response.headers)


def test_given_desktop_client_when_export_then_poll_reaches_done_and_file_downloads(tmp_path, monkeypatch) -> None:
	# given
	client = TestClient(_library_with_photo(tmp_path, monkeypatch))
	# when
	started = client.post("/api/gallery/export", json={"relative_path": "a.jpg", "format": "jpeg"})
	job = _wait_for_export(client, started.json()["job_id"])
	# then
	assert job["phase"] == "done"
	assert job["download_url"] == f"/api/gallery/export/{job['job_id']}/file"
	assert client.get(job["download_url"]).content == b"\xff\xd8\xff\xd9"
