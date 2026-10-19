from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from tests.unit.fakes import FakeDeviceRepository
from tests.unit.passcode_fakes import FakeClock, FakePasscodeCrypto, FakePasscodeStore

from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.bootstrap.services import create_app
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseErrorKind, DeviceEntry


pytestmark = pytest.mark.integration


def _app_with_fake() -> tuple[FastAPI, FakeDeviceRepository]:
	app = create_app()
	devices = FakeDeviceRepository()
	app.state.services._device_repos[ConnectionMethod.ADB] = devices
	return app, devices


def _body(path: str = "", **extra: object) -> dict[str, object]:
	return {"method": "adb", "device_id": "dev1", "path": path, **extra}


def test_given_root_when_post_list_then_entries_sorted_with_metadata() -> None:
	# given
	app, devices = _app_with_fake()
	devices.tree[""] = [DeviceEntry("a.txt", False, 5, 9), DeviceEntry("DCIM", True)]
	client = TestClient(app)
	# when
	response = client.post("/api/device/list", json=_body())
	# then
	assert response.status_code == 200
	data = response.json()
	assert [e["name"] for e in data["entries"]] == ["DCIM", "a.txt"]
	assert data["entries"][1] == {"name": "a.txt", "is_dir": False, "size": 5, "mtime": 9}
	assert data["next_cursor"] is None
	assert data["total"] == 2
	assert devices.list_directory_calls == [""]


@pytest.mark.parametrize("path", ["../data", "a/../../b", "a\x00b"])
def test_given_escaping_path_when_post_list_then_400_and_no_device_call(path: str) -> None:
	# given
	app, devices = _app_with_fake()
	client = TestClient(app)
	# when
	response = client.post("/api/device/list", json=_body(path))
	# then
	assert response.status_code == 400
	assert response.json()["detail"]["error"] == "invalid_path"
	assert devices.list_directory_calls == []


@pytest.mark.parametrize(
	("kind", "status"),
	[
		(DeviceBrowseErrorKind.PERMISSION_DENIED, 403),
		(DeviceBrowseErrorKind.UNAUTHORIZED, 403),
		(DeviceBrowseErrorKind.UNPLUGGED, 409),
		(DeviceBrowseErrorKind.TIMEOUT, 504),
		(DeviceBrowseErrorKind.NOT_FOUND, 404),
	],
)
def test_given_device_error_when_post_list_then_kind_in_detail(kind: DeviceBrowseErrorKind, status: int) -> None:
	# given
	app, devices = _app_with_fake()
	devices.browse_errors["Android/data"] = kind
	client = TestClient(app)
	# when
	response = client.post("/api/device/list", json=_body("Android/data"))
	# then
	assert response.status_code == status
	assert response.json()["detail"]["error"] == kind.value


def test_given_wifi_method_when_post_list_then_400() -> None:
	# given
	client = TestClient(create_app())
	# when
	response = client.post("/api/device/list", json={"method": "wifi", "device_id": "x", "path": ""})
	# then
	assert response.status_code == 400


def test_given_passcode_and_lan_client_when_post_list_then_401() -> None:
	# given
	app, _devices = _app_with_fake()
	passcode = NetworkPasscode(FakePasscodeStore(), FakePasscodeCrypto(), FakeClock())
	passcode.load()
	passcode.set_passcode("123456")
	app.state.services.network_passcode = passcode

	async def lan_app(scope, receive, send):  # type: ignore[no-untyped-def]
		scope = dict(scope)
		if scope["type"] in {"http", "websocket"}:
			scope["client"] = ("10.0.0.2", 43210)
		await app(scope, receive, send)

	client = TestClient(lan_app)
	# when
	response = client.post("/api/device/list", json=_body())
	# then
	assert response.status_code == 401
	assert response.json() == {"detail": "passcode-required"}


def test_given_lan_client_without_passcode_when_post_list_then_403_desktop_only() -> None:
	# given
	app, devices = _app_with_fake()

	async def lan_app(scope, receive, send):  # type: ignore[no-untyped-def]
		scope = dict(scope)
		if scope["type"] in {"http", "websocket"}:
			scope["client"] = ("10.0.0.2", 43210)
		await app(scope, receive, send)

	client = TestClient(lan_app)
	# when
	response = client.post("/api/device/list", json=_body())
	# then
	assert response.status_code == 403
	assert devices.list_directory_calls == []


def test_given_extract_extras_when_snapshot_then_start_gate_counts_them() -> None:
	# given
	app, _devices = _app_with_fake()
	client = TestClient(app)
	# when
	response = client.post("/api/extract/extras", json={"paths": ["WhatsApp/Media", "whatsapp/media"]})
	# then
	assert response.status_code == 200
	assert response.json()["extract_extra_paths"] == ["WhatsApp/Media"]
