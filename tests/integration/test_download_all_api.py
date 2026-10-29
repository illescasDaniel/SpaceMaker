from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from tests.unit.passcode_fakes import FakeClock, FakePasscodeCrypto, FakePasscodeStore

from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.bootstrap.services import create_app
from spacemaker.domain.app_module import AppModule
from spacemaker.domain.download_all import DownloadAllBuildError
from spacemaker.domain.transfer_session import TransferOrigin


pytestmark = pytest.mark.integration


def _lan(app, host: str = "10.0.0.2") -> TestClient:
	async def lan_app(scope, receive, send):  # type: ignore[no-untyped-def]
		scope = dict(scope)
		if scope["type"] in {"http", "websocket"}:
			scope["client"] = (host, 43210)
		await app(scope, receive, send)

	return TestClient(lan_app)


def _transfer_app(tmp_path, monkeypatch, names=("a.txt", "b.txt")):
	monkeypatch.setenv("HOME", str(tmp_path))
	app = create_app()
	services = app.state.services
	services._documents_receive_root = str(tmp_path / "Documents" / "SpaceMaker")
	services.enter_module(AppModule.TRANSFER_FILES)
	for index, name in enumerate(names):
		temp = tmp_path / "in" / str(index) / name
		temp.parent.mkdir(parents=True, exist_ok=True)
		temp.write_bytes(name.encode())
		services.handle_transfer_upload_file(
			services._transfer_session_token, requested_name=name, temp_path=str(temp), origin=TransferOrigin.PHONE
		)
	return app, services


def _share_app(tmp_path, monkeypatch, names=("a.txt", "b.txt")):
	monkeypatch.setenv("HOME", str(tmp_path))
	app = create_app()
	services = app.state.services
	paths = []
	for name in names:
		path = tmp_path / "shared" / name
		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_bytes(name.encode())
		paths.append(str(path))
	services.set_share_selection(paths)
	return app, services


def _names(content: bytes) -> list[str]:
	with zipfile.ZipFile(io.BytesIO(content)) as archive:
		return sorted(archive.namelist())


def test_given_share_session_when_lan_get_download_all_then_zip_attachment_and_temp_deleted(
	tmp_path, monkeypatch
) -> None:
	# given
	app, services = _share_app(tmp_path, monkeypatch)
	built: list[Path] = []
	original = services.share_download_all

	def spy(token):
		path = original(token)
		built.append(path)
		return path

	services.share_download_all = spy
	# when
	response = _lan(app).get(f"/api/share/download-all?t={services._share_session_token}")
	# then
	assert response.status_code == 200
	assert response.headers["content-type"] == "application/zip"
	assert "SpaceMaker-share.zip" in response.headers["content-disposition"]
	assert _names(response.content) == ["a.txt", "b.txt"]
	assert len(built) == 1
	assert not built[0].exists()
	services.shutdown()


def test_given_transfer_session_when_lan_get_download_all_then_zip_attachment_and_temp_deleted(
	tmp_path, monkeypatch
) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	built: list[Path] = []
	original = services.transfer_download_all

	def spy(token):
		path = original(token)
		built.append(path)
		return path

	services.transfer_download_all = spy
	# when
	response = _lan(app).get(f"/api/transfer/download-all?t={services._transfer_session_token}")
	# then
	assert response.status_code == 200
	assert response.headers["content-type"] == "application/zip"
	assert "SpaceMaker-transfer.zip" in response.headers["content-disposition"]
	assert _names(response.content) == ["a.txt", "b.txt"]
	assert not built[0].exists()
	services.shutdown()


@pytest.mark.parametrize("path", ["/api/share/download-all", "/api/transfer/download-all"])
def test_given_wrong_token_when_get_download_all_then_403(tmp_path, monkeypatch, path) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	# when
	response = TestClient(app).get(f"{path}?t=wrong")
	# then
	assert response.status_code == 403
	services.shutdown()


def test_given_ended_session_when_get_transfer_download_all_then_403(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	token = services._transfer_session_token
	services.leave_module_for_home()
	# when
	response = TestClient(app).get(f"/api/transfer/download-all?t={token}")
	# then
	assert response.status_code == 403
	services.shutdown()


def test_given_valid_session_without_items_when_get_transfer_download_all_then_404_nothing_to_download(
	tmp_path, monkeypatch
) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch, names=())
	# when
	response = _lan(app).get(f"/api/transfer/download-all?t={services._transfer_session_token}")
	# then
	assert response.status_code == 404
	assert response.json()["detail"] == "nothing to download"
	services.shutdown()


def test_given_all_share_files_vanished_when_get_share_download_all_then_404(tmp_path, monkeypatch) -> None:
	# given
	app, services = _share_app(tmp_path, monkeypatch)
	for name in ("a.txt", "b.txt"):
		(tmp_path / "shared" / name).unlink()
	# when
	response = _lan(app).get(f"/api/share/download-all?t={services._share_session_token}")
	# then
	assert response.status_code == 404
	services.shutdown()


def test_given_build_failure_when_get_transfer_download_all_then_500_and_session_unchanged(
	tmp_path, monkeypatch
) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)

	class _Failing:
		def build(self, kind, items, destination) -> None:
			raise DownloadAllBuildError("disk full")

	services.download_all = _Failing()
	token = services._transfer_session_token
	# when
	response = _lan(app).get(f"/api/transfer/download-all?t={token}")
	# then
	assert response.status_code == 500
	assert response.json()["detail"] == "could not build zip"
	assert len(services.transfer_manifest(token)) == 2
	services.shutdown()


def test_given_extra_file_id_and_path_params_when_get_transfer_download_all_then_ignored(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	secret = tmp_path / "secret.txt"
	secret.write_text("nope")
	token = services._transfer_session_token
	# when
	response = _lan(app).get(f"/api/transfer/download-all?t={token}&file_id=anything&path={secret}")
	# then
	assert response.status_code == 200
	assert _names(response.content) == ["a.txt", "b.txt"]
	services.shutdown()


def test_given_extra_params_when_get_share_download_all_then_only_manifest_zipped(tmp_path, monkeypatch) -> None:
	# given
	app, services = _share_app(tmp_path, monkeypatch)
	secret = tmp_path / "secret.txt"
	secret.write_text("nope")
	# when
	response = _lan(app).get(f"/api/share/download-all?t={services._share_session_token}&file_id=x&path={secret}")
	# then
	assert response.status_code == 200
	assert _names(response.content) == ["a.txt", "b.txt"]
	services.shutdown()


def test_given_loopback_client_when_post_save_all_then_saved_path_returned(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	# when
	response = TestClient(app).post("/api/transfer/save-all")
	# then
	assert response.status_code == 200
	body = response.json()
	assert body["saved_name"] == "SpaceMaker-transfer.zip"
	assert set(body) >= {"saved_path", "saved_name", "saved_path_display"}
	assert Path(body["saved_path"]).is_file()
	services.shutdown()


def test_given_lan_client_when_post_save_all_then_403_desktop_only(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	# when
	response = _lan(app).post("/api/transfer/save-all")
	# then
	assert response.status_code == 403
	assert not (tmp_path / "Documents" / "SpaceMaker" / "SpaceMaker-transfer.zip").exists()
	services.shutdown()


def test_given_ended_session_when_post_save_all_then_403(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	services.leave_module_for_home()
	# when
	response = TestClient(app).post("/api/transfer/save-all")
	# then
	assert response.status_code == 403
	services.shutdown()


def test_given_empty_session_when_post_save_all_then_404(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch, names=())
	# when
	response = TestClient(app).post("/api/transfer/save-all")
	# then
	assert response.status_code == 404
	services.shutdown()


def test_given_build_failure_when_post_save_all_then_500(tmp_path, monkeypatch) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)

	class _Failing:
		def build(self, kind, items, destination) -> None:
			raise DownloadAllBuildError("disk full")

	services.download_all = _Failing()
	# when
	response = TestClient(app).post("/api/transfer/save-all")
	# then
	assert response.status_code == 500
	services.shutdown()


@pytest.mark.parametrize("path", ["/api/share/download-all", "/api/transfer/download-all"])
def test_given_passcode_and_locked_lan_client_when_get_download_all_then_401(tmp_path, monkeypatch, path) -> None:
	# given
	app, services = _transfer_app(tmp_path, monkeypatch)
	passcode = NetworkPasscode(FakePasscodeStore(), FakePasscodeCrypto(), FakeClock())
	passcode.load()
	passcode.set_passcode("123456")
	services.network_passcode = passcode
	# when
	response = _lan(app).get(f"{path}?t={services._transfer_session_token}")
	# then
	assert response.status_code == 401
	services.shutdown()
