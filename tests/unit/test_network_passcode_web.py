from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.unit.passcode_fakes import FakeClock, FakePasscodeCrypto, FakePasscodeStore

from spacemaker.adapters.inbound.web.app import create_fastapi_app
from spacemaker.adapters.inbound.web.session import AppSession
from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.bootstrap.services import AppServices


PHONE = ("192.168.1.50", 50000)
HTML = {"Accept": "text/html"}


class _StubServices(AppServices):
	def __init__(self, library_root: str, passcode: NetworkPasscode) -> None:
		self.session = AppSession(library_root=library_root)
		self.filesystem = LocalFileSystem()
		self.network_passcode = passcode
		self.port = 8765
		self.bind_host = "127.0.0.1"

	def shutdown(self, *, timeout_seconds: float = 10.0) -> None:
		pass

	def push_state(self) -> None:
		pass


@pytest.fixture
def passcode() -> NetworkPasscode:
	use_case = NetworkPasscode(FakePasscodeStore(), FakePasscodeCrypto(), FakeClock())
	use_case.load()
	return use_case


@pytest.fixture
def desktop(tmp_path: Path, passcode: NetworkPasscode) -> Iterator[TestClient]:
	with TestClient(create_fastapi_app(_StubServices(str(tmp_path), passcode))) as client:
		yield client


@pytest.fixture
def phone(tmp_path: Path, passcode: NetworkPasscode) -> Iterator[TestClient]:
	with TestClient(create_fastapi_app(_StubServices(str(tmp_path), passcode)), client=PHONE) as client:
		yield client


def test_given_no_passcode_when_phone_requests_gallery_page_then_served(phone: TestClient) -> None:
	# given
	headers = HTML
	# when
	response = phone.get("/gallery", headers=headers)
	# then
	assert response.status_code == 200


def test_given_desktop_when_set_passcode_then_enabled_status_without_secrets(desktop: TestClient) -> None:
	# given
	body = {"passcode": "hunter2"}
	# when
	put = desktop.put("/api/network-passcode", json=body)
	status = desktop.get("/api/network-passcode")
	# then
	assert put.status_code == 200
	assert status.json() == {"enabled": True, "corrupt_warning": False}
	assert "hunter2" not in put.text + status.text


def test_given_desktop_when_set_short_passcode_then_400(desktop: TestClient) -> None:
	# given
	body = {"passcode": "abc"}
	# when
	response = desktop.put("/api/network-passcode", json=body)
	# then
	assert response.status_code == 400
	assert desktop.get("/api/network-passcode").json()["enabled"] is False


def test_given_passcode_when_phone_calls_api_without_login_then_401_passcode_required(
	desktop: TestClient, phone: TestClient
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	response = phone.get("/api/gallery/timeline")
	# then
	assert response.status_code == 401
	assert response.json() == {"detail": "passcode-required"}


def test_given_passcode_when_phone_navigates_without_login_then_unlock_page(
	desktop: TestClient, phone: TestClient
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	response = phone.get("/gallery", headers=HTML)
	# then
	assert response.status_code == 401
	assert "text/html" in response.headers["content-type"]
	assert "Unlock" in response.text


@pytest.mark.parametrize("path", ["/static/unlock.css", "/static/js/unlock.js", "/favicon.ico"])
def test_given_passcode_when_phone_requests_unlock_assets_then_not_challenged(
	desktop: TestClient, phone: TestClient, path: str
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	response = phone.get(path)
	# then
	assert response.status_code != 401


@pytest.mark.parametrize("path", ["/static/js/passcode.js", "/static/index.html", "/static/unlock.css/../index.html"])
def test_given_passcode_when_phone_requests_other_static_files_then_401(
	desktop: TestClient, phone: TestClient, path: str
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	response = phone.get(path)
	# then
	assert response.status_code == 401


def test_given_passcode_when_desktop_requests_then_no_login_needed(desktop: TestClient) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	response = desktop.get("/api/network-passcode")
	# then
	assert response.status_code == 200


def test_given_correct_passcode_when_phone_unlocks_then_cookie_set_and_gallery_loads(
	desktop: TestClient, phone: TestClient
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	unlock = phone.post("/api/unlock", json={"passcode": "hunter2"})
	page = phone.get("/gallery", headers=HTML)
	# then
	assert unlock.status_code == 200
	set_cookie = unlock.headers["set-cookie"].lower()
	assert "httponly" in set_cookie
	assert "samesite=strict" in set_cookie
	assert page.status_code == 200


def test_given_qr_token_when_phone_unlocks_then_logged_in(
	desktop: TestClient, phone: TestClient, passcode: NetworkPasscode
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	token = passcode.qr_token()
	# when
	unlock = phone.post("/api/unlock", json={"token": token})
	page = phone.get("/gallery", headers=HTML)
	# then
	assert unlock.status_code == 200
	assert page.status_code == 200


def test_given_wrong_passcode_when_phone_unlocks_then_401_wrong(desktop: TestClient, phone: TestClient) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when
	response = phone.post("/api/unlock", json={"passcode": "nope"})
	# then
	assert response.status_code == 401
	assert response.json()["detail"] == "wrong-passcode"
	assert "set-cookie" not in response.headers


def test_given_five_wrong_tries_when_phone_unlocks_then_429_with_retry_after(
	desktop: TestClient, phone: TestClient
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	for _ in range(5):
		phone.post("/api/unlock", json={"passcode": "nope"})
	# when
	response = phone.post("/api/unlock", json={"passcode": "hunter2"})
	# then
	assert response.status_code == 429
	assert response.json()["retry_after_seconds"] > 0
	assert int(response.headers["retry-after"]) > 0


def test_given_logged_in_phone_when_passcode_changed_then_api_returns_401(
	desktop: TestClient, phone: TestClient
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	phone.post("/api/unlock", json={"passcode": "hunter2"})
	# when
	desktop.put("/api/network-passcode", json={"passcode": "new-passcode"})
	response = phone.get("/api/gallery/timeline")
	# then
	assert response.status_code == 401


def test_given_logged_in_phone_when_passcode_cleared_then_served_openly(desktop: TestClient, phone: TestClient) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	phone.post("/api/unlock", json={"passcode": "hunter2"})
	# when
	assert desktop.delete("/api/network-passcode").status_code == 200
	# then
	assert phone.get("/gallery", headers=HTML).status_code == 200


def test_given_logged_in_phone_when_calling_desktop_only_route_then_403(desktop: TestClient, phone: TestClient) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	phone.post("/api/unlock", json={"passcode": "hunter2"})
	# when
	response = phone.put("/api/network-passcode", json={"passcode": "evil-pass"})
	# then
	assert response.status_code == 403
	assert response.json()["detail"] == "desktop-only"


def test_given_passcode_when_phone_requests_media_and_thumbs_then_401(desktop: TestClient, phone: TestClient) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	# when / then
	assert phone.get("/media/a.avif").status_code == 401
	assert phone.get("/thumbs/a.avif").status_code == 401
	assert phone.delete("/api/gallery/item", params={"path": "a.avif"}).status_code == 401


def test_given_enabled_when_desktop_snapshot_urls_built_then_qr_fragment_appended(
	desktop: TestClient, passcode: NetworkPasscode
) -> None:
	# given
	desktop.put("/api/network-passcode", json={"passcode": "hunter2"})
	token = passcode.qr_token()
	# when
	body = desktop.get("/api/server-info").json()
	# then
	assert body["gallery_url"].endswith(f"/gallery#k={token}")
