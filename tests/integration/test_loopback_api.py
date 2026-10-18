from __future__ import annotations

import re

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


def _batch_app(tmp_path, monkeypatch, *, encoder=None):
	from tests.unit.fakes import FakeTrash

	from spacemaker.domain.gallery_batch import VideoExportEncoder

	app = _library_with_photo(tmp_path, monkeypatch)
	services = app.state.services
	processed = tmp_path / "lib" / "processed"
	(processed / "b.png").write_bytes(b"png")
	(processed / "v.mov").write_bytes(b"mov")

	def fake_jpeg(source: str, destination: str) -> None:
		from pathlib import Path

		Path(destination).parent.mkdir(parents=True, exist_ok=True)
		Path(destination).write_bytes(b"\xff\xd8\xff\xd9")

	cpu_flags: list[bool] = []

	def fake_h264(source: str, destination: str, *, on_progress=None, use_cpu: bool = False) -> None:
		from pathlib import Path

		cpu_flags.append(use_cpu)
		Path(destination).parent.mkdir(parents=True, exist_ok=True)
		Path(destination).write_bytes(b"mp4")

	monkeypatch.setattr(services.converter, "encode_image_to_jpeg", fake_jpeg)
	monkeypatch.setattr(services.converter, "encode_video_to_h264_aac", fake_h264)
	monkeypatch.setattr(
		services.converter, "friendly_video_encoder", lambda: encoder or VideoExportEncoder.HARDWARE_H264
	)
	monkeypatch.setattr(services.probe, "probe_video", lambda _path: None)
	trash = FakeTrash()
	services.trash_gallery_items._trash = trash
	return app, trash, cpu_flags


def _wait_for_batch(client: TestClient, job_id: str) -> dict[str, object]:
	import time

	deadline = time.monotonic() + 10
	while time.monotonic() < deadline:
		job = client.get(f"/api/gallery/batch/convert/{job_id}").json()
		if job["phase"] != "running":
			return job
		time.sleep(0.05)
	raise AssertionError("batch never finished")


def test_given_selection_when_batch_convert_then_zip_downloads_once_and_is_cleaned_up(tmp_path, monkeypatch) -> None:
	# given
	import io
	import zipfile

	app, _trash, _h264 = _batch_app(tmp_path, monkeypatch)
	client = TestClient(app)
	# when
	started = client.post("/api/gallery/batch/convert", json={"relative_paths": ["a.jpg", "b.png", "v.mov"]})
	job = _wait_for_batch(client, started.json()["job_id"])
	download = client.get(job["download_url"])
	# then
	assert started.status_code == 200
	assert job["phase"] == "done"
	assert str(tmp_path) not in str(job)
	with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
		assert sorted(n.split("/")[-1] for n in archive.namelist()) == ["a.jpg", "b.png.jpg", "v.mov.mp4"]
		assert all(re.fullmatch(r"\d{4}/\d{2}/[^/]+", n) for n in archive.namelist())
	assert not any((tmp_path / "lib" / ".exports" / ".batch").glob("*/*.zip"))
	assert client.get(job["download_url"]).status_code == 404
	assert (tmp_path / "lib" / "processed" / "b.png").read_bytes() == b"png"


def test_given_selection_when_batch_download_then_zip_has_stored_bytes_unconverted(tmp_path, monkeypatch) -> None:
	# given
	import io
	import zipfile

	app, _trash, cpu_flags = _batch_app(tmp_path, monkeypatch)
	client = TestClient(app)
	# when
	started = client.post("/api/gallery/batch/download", json={"relative_paths": ["a.jpg", "b.png"]})
	job = _wait_for_batch(client, started.json()["job_id"])
	response = client.get(job["download_url"])
	# then
	assert job["kind"] == "download"
	assert response.status_code == 200
	with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
		assert sorted(n.split("/")[-1] for n in archive.namelist()) == ["a.jpg", "b.png"]
		png = next(n for n in archive.namelist() if n.endswith("/b.png"))
		assert archive.read(png) == b"png"
	assert cpu_flags == []


def test_given_unsafe_path_when_batch_download_then_403(tmp_path, monkeypatch) -> None:
	# given
	app, _trash, _flags = _batch_app(tmp_path, monkeypatch)
	client = TestClient(app)
	# when
	response = client.post("/api/gallery/batch/download", json={"relative_paths": ["../x.jpg"]})
	# then
	assert response.status_code == 403


def test_given_unsafe_or_too_many_paths_when_batch_then_rejected_before_work(tmp_path, monkeypatch) -> None:
	# given
	app, trash, _h264 = _batch_app(tmp_path, monkeypatch)
	client = TestClient(app)
	# when
	unsafe = client.post("/api/gallery/batch/trash", json={"relative_paths": ["a.jpg", "../outside.jpg"]})
	too_many = client.post("/api/gallery/batch/convert", json={"relative_paths": [f"{i}.jpg" for i in range(501)]})
	# then
	assert unsafe.status_code == 403
	assert too_many.status_code == 400
	assert trash.trashed == []
	assert (tmp_path / "lib" / "processed" / "a.jpg").is_file()


def test_given_symlink_escaping_processed_when_batch_trash_then_403_and_nothing_trashed(tmp_path, monkeypatch) -> None:
	# given
	app, trash, _h264 = _batch_app(tmp_path, monkeypatch)
	client = TestClient(app)
	outside = tmp_path / "outside.jpg"
	outside.write_bytes(b"secret")
	(tmp_path / "lib" / "processed" / "link.jpg").symlink_to(outside)
	# when
	response = client.post("/api/gallery/batch/trash", json={"relative_paths": ["a.jpg", "link.jpg"]})
	# then
	assert response.status_code == 403
	assert trash.trashed == []
	assert outside.is_file()


def test_given_no_gpu_when_batch_convert_unconfirmed_then_409_and_nothing_starts_then_confirmed_runs_on_cpu(
	tmp_path, monkeypatch
) -> None:
	# given
	from spacemaker.domain.gallery_batch import VideoExportEncoder

	app, _trash, h264 = _batch_app(tmp_path, monkeypatch, encoder=VideoExportEncoder.CPU_H264)
	client = TestClient(app)
	body = {"relative_paths": ["b.png", "v.mov"]}
	# when
	refused = client.post("/api/gallery/batch/convert", json=body)
	confirmed = client.post("/api/gallery/batch/convert", json={**body, "allow_cpu_encode": True})
	job = _wait_for_batch(client, confirmed.json()["job_id"])
	# then
	assert refused.status_code == 409
	assert refused.json()["detail"] == {"code": "cpu_confirm_required", "video_count": 1}
	assert confirmed.status_code == 200
	assert job["phase"] == "done"
	assert h264 == [True]


def test_given_no_gpu_when_single_mp4_export_unconfirmed_then_409(tmp_path, monkeypatch) -> None:
	# given
	from spacemaker.domain.gallery_batch import VideoExportEncoder

	app, _trash, h264 = _batch_app(tmp_path, monkeypatch, encoder=VideoExportEncoder.CPU_H264)
	client = TestClient(app)
	# when
	refused = client.post("/api/gallery/export", json={"relative_path": "v.mov", "format": "h264_aac"})
	# then
	assert refused.status_code == 409
	assert h264 == []


def test_given_selection_when_batch_trash_then_files_trashed_and_removed_from_gallery(tmp_path, monkeypatch) -> None:
	# given
	app, trash, _h264 = _batch_app(tmp_path, monkeypatch)
	client = TestClient(app)
	# when
	response = client.post("/api/gallery/batch/trash", json={"relative_paths": ["a.jpg", "b.png"]})
	# then
	assert response.status_code == 200
	assert [r["outcome"] for r in response.json()["results"]] == ["trashed", "trashed"]
	assert len(trash.trashed) == 2
	assert not (tmp_path / "lib" / "processed" / "a.jpg").exists()
