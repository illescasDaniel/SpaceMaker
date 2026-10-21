from __future__ import annotations

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from tests.unit.fakes import FakeDeviceRepository, FakeUserPreferences
from tests.unit.passcode_fakes import FakeClock, FakePasscodeCrypto, FakePasscodeStore

from spacemaker.application.network_passcode import NetworkPasscode
from spacemaker.bootstrap.services import create_app
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_browse import DeviceBrowseErrorKind, DeviceEntry
from spacemaker.domain.device_view import DeviceViewMode, DeviceViewSetting


pytestmark = pytest.mark.integration

GRID_FIELDS = {"entry_count", "media_count", "folder_view", "stored_view"}


def _app() -> tuple[FastAPI, FakeDeviceRepository, FakeUserPreferences]:
	app = create_app()
	devices = FakeDeviceRepository()
	prefs = FakeUserPreferences()
	app.state.services._device_repos[ConnectionMethod.ADB] = devices
	app.state.services.user_preferences = prefs
	return app, devices, prefs


def _lan(app: FastAPI) -> TestClient:
	async def lan_app(scope, receive, send):  # type: ignore[no-untyped-def]
		scope = dict(scope)
		if scope["type"] in {"http", "websocket"}:
			scope["client"] = ("10.0.0.2", 43210)
		await app(scope, receive, send)

	return TestClient(lan_app)


def _body(path: str = "", **extra: object) -> dict[str, object]:
	return {"method": "adb", "device_id": "dev1", "path": path, **extra}


def _put(client: TestClient, body: object):  # type: ignore[no-untyped-def]
	return client.put("/api/device/view", json=body)


# POST /api/device/list: grid fields


def test_given_camera_folder_when_post_list_page_1_then_counts_and_hints_present() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["DCIM/Camera"] = [
		DeviceEntry("a.jpg", False),
		DeviceEntry("b.mp4", False),
		DeviceEntry("n.txt", False),
	]
	client = TestClient(app)
	# when
	data = client.post("/api/device/list", json=_body("DCIM/Camera")).json()
	# then
	assert data["entry_count"] == 3
	assert data["media_count"] == 2
	assert data["folder_view"] == "grid"
	assert data["stored_view"] is None


def test_given_untyped_folder_when_post_list_then_folder_view_null() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["Backup2024"] = [DeviceEntry(f"p{i}.jpg", False) for i in range(4)]
	client = TestClient(app)
	# when
	data = client.post("/api/device/list", json=_body("Backup2024")).json()
	# then
	assert data["folder_view"] is None
	assert (data["entry_count"], data["media_count"]) == (4, 4)


def test_given_photos_under_documents_when_post_list_then_folder_view_list_despite_media() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["Documents/Trip"] = [DeviceEntry(f"p{i}.jpg", False) for i in range(50)]
	client = TestClient(app)
	# when
	data = client.post("/api/device/list", json=_body("Documents/Trip")).json()
	# then
	assert data["folder_view"] == "list"
	assert data["media_count"] == 50


def test_given_stored_choice_when_post_list_then_stored_view_reported() -> None:
	# given
	app, devices, prefs = _app()
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	devices.tree["DCIM/Camera"] = [DeviceEntry("a.jpg", False)]
	client = TestClient(app)
	# when
	data = client.post("/api/device/list", json=_body("DCIM/Camera")).json()
	# then
	assert data["stored_view"] == "list"
	assert data["folder_view"] == "grid"


def test_given_hidden_and_query_when_post_list_then_counts_follow_hidden_and_ignore_query() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["Misc"] = (
		[DeviceEntry(f"p{i}.jpg", False) for i in range(10)]
		+ [DeviceEntry(f"d{i}.pdf", False) for i in range(10)]
		+ [DeviceEntry(f".h{i}.jpg", False) for i in range(20)]
	)
	client = TestClient(app)
	# when
	plain = client.post("/api/device/list", json=_body("Misc")).json()
	hidden = client.post("/api/device/list", json=_body("Misc", show_hidden=True)).json()
	filtered = client.post("/api/device/list", json=_body("Misc", show_hidden=True, query=".pdf")).json()
	# then
	assert (plain["entry_count"], plain["media_count"]) == (20, 10)
	assert (hidden["entry_count"], hidden["media_count"]) == (40, 30)
	assert (filtered["entry_count"], filtered["media_count"]) == (40, 30)
	assert filtered["total"] == 10
	assert devices.list_directory_calls == ["Misc"]


def test_given_second_page_when_post_list_with_cursor_then_all_four_grid_fields_omitted() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["DCIM"] = [DeviceEntry(f"f{i:03d}.jpg", False) for i in range(250)]
	client = TestClient(app)
	first = client.post("/api/device/list", json=_body("DCIM")).json()
	# when
	second = client.post("/api/device/list", json=_body("DCIM", cursor=first["next_cursor"])).json()
	# then
	assert GRID_FIELDS <= set(first)
	assert GRID_FIELDS.isdisjoint(second)
	assert len(second["entries"]) == 100


def test_given_sort_restart_without_cursor_when_post_list_then_page_1_fields_present_again() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["DCIM"] = [DeviceEntry(f"f{i}.jpg", False, size=i) for i in range(5)]
	client = TestClient(app)
	# when
	data = client.post("/api/device/list", json=_body("DCIM", sort="size", order="desc")).json()
	# then
	assert GRID_FIELDS <= set(data)


def test_given_list_request_when_post_list_then_view_memory_never_written() -> None:
	# given
	app, devices, prefs = _app()
	devices.tree["DCIM"] = [DeviceEntry("a.jpg", False)]
	client = TestClient(app)
	# when
	client.post("/api/device/list", json=_body("DCIM"))
	# then
	assert prefs.picker_view_writes == []


@pytest.mark.parametrize(
	("kind", "status"),
	[
		(DeviceBrowseErrorKind.UNPLUGGED, 409),
		(DeviceBrowseErrorKind.PERMISSION_DENIED, 403),
		(DeviceBrowseErrorKind.UNAUTHORIZED, 403),
		(DeviceBrowseErrorKind.TIMEOUT, 504),
	],
)
def test_given_listing_error_when_post_list_then_hints_present_and_counts_omitted(
	kind: DeviceBrowseErrorKind, status: int
) -> None:
	# given
	app, devices, prefs = _app()
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	devices.browse_errors["DCIM/Camera"] = kind
	client = TestClient(app)
	# when
	response = client.post("/api/device/list", json=_body("DCIM/Camera"))
	# then
	assert response.status_code == status
	detail = response.json()["detail"]
	assert detail["error"] == kind.value
	assert detail["folder_view"] == "grid"
	assert detail["stored_view"] == "list"
	assert "entry_count" not in detail
	assert "media_count" not in detail


def test_given_listing_error_in_untyped_folder_when_post_list_then_hints_are_null() -> None:
	# given
	app, devices, _prefs = _app()
	devices.browse_errors["Secret"] = DeviceBrowseErrorKind.PERMISSION_DENIED
	client = TestClient(app)
	# when
	detail = client.post("/api/device/list", json=_body("Secret")).json()["detail"]
	# then
	assert detail["folder_view"] is None
	assert detail["stored_view"] is None


# PUT /api/device/view


@pytest.mark.parametrize(("view", "expected"), [("list", DeviceViewMode.LIST), ("grid", DeviceViewMode.GRID)])
def test_given_list_or_grid_when_put_view_then_204_and_stored(view: str, expected: DeviceViewMode) -> None:
	# given
	app, devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, {"path": "DCIM/Camera", "view": view})
	# then
	assert response.status_code == 204
	assert dict(prefs.get_device_picker_views()) == {"DCIM/Camera": expected}
	assert devices.list_directory_calls == []
	assert devices.device_calls == 0


@pytest.mark.parametrize(
	("path", "key"), [("/etc/passwd", "etc/passwd"), ("/data/data/x", "data/data/x"), ("\\\\x\\y", "x/y")]
)
def test_given_absolute_path_when_put_view_then_treated_as_storage_relative_like_list(path: str, key: str) -> None:
	# given
	app, devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, {"path": path, "view": "grid"})
	# then (same rule as /api/device/list: the leading "/" is dropped, the path stays inside phone storage)
	assert response.status_code == 204
	assert dict(prefs.get_device_picker_views()) == {key: DeviceViewMode.GRID}
	assert devices.device_calls == 0


def test_given_stored_choice_when_put_view_auto_then_204_and_removed() -> None:
	# given
	app, _devices, prefs = _app()
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	client = TestClient(app)
	# when
	response = _put(client, {"path": "DCIM/Camera", "view": "auto"})
	# then
	assert response.status_code == 204
	assert dict(prefs.get_device_picker_views()) == {}


def test_given_nothing_stored_when_put_view_auto_then_204() -> None:
	# given
	app, _devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, {"path": "Never/Stored", "view": "auto"})
	# then
	assert response.status_code == 204
	assert dict(prefs.get_device_picker_views()) == {}


def test_given_root_path_when_put_view_then_204_and_root_key_stored() -> None:
	# given
	app, _devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, {"path": "", "view": "grid"})
	# then
	assert response.status_code == 204
	assert dict(prefs.get_device_picker_views()) == {"": DeviceViewMode.GRID}


def test_given_prefixed_path_when_put_view_then_normalized_key_stored() -> None:
	# given
	app, _devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, {"path": "/sdcard/Pictures/", "view": "list"})
	# then
	assert response.status_code == 204
	assert dict(prefs.get_device_picker_views()) == {"Pictures": DeviceViewMode.LIST}


def test_given_stored_choice_when_put_then_list_reports_it_and_auto_forgets_it() -> None:
	# given
	app, devices, _prefs = _app()
	devices.tree["DCIM/Camera"] = [DeviceEntry("a.jpg", False)]
	client = TestClient(app)
	# when
	_put(client, {"path": "DCIM/Camera", "view": "list"})
	stored = client.post("/api/device/list", json=_body("DCIM/Camera")).json()
	_put(client, {"path": "DCIM/Camera", "view": "auto"})
	forgotten = client.post("/api/device/list", json=_body("DCIM/Camera")).json()
	# then
	assert stored["stored_view"] == "list"
	assert forgotten["stored_view"] is None


@pytest.mark.parametrize(
	"body",
	[
		{"path": "DCIM", "view": "tiles"},
		{"path": "DCIM", "view": "AUTO"},
		{"path": "DCIM", "view": None},
		{"path": "DCIM"},
		{"view": "grid"},
		{"path": 5, "view": "grid"},
		["DCIM", "grid"],
		"grid",
	],
)
def test_given_bad_view_or_malformed_body_when_put_view_then_422_and_nothing_stored(body: object) -> None:
	# given
	app, _devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, body)
	# then
	assert response.status_code == 422
	assert prefs.picker_view_writes == []


@pytest.mark.parametrize("path", ["../data", "a/../../b", "a\x00b"])
def test_given_escaping_path_when_put_view_then_400_invalid_path_and_nothing_stored(path: str) -> None:
	# given
	app, devices, prefs = _app()
	client = TestClient(app)
	# when
	response = _put(client, {"path": path, "view": "grid"})
	# then
	assert response.status_code == 400
	assert response.json()["detail"]["error"] == "invalid_path"
	assert prefs.picker_view_writes == []
	assert devices.device_calls == 0


def test_given_lan_client_when_put_view_then_403_desktop_only_and_nothing_stored() -> None:
	# given
	app, devices, prefs = _app()
	client = _lan(app)
	# when
	response = _put(client, {"path": "DCIM", "view": "grid"})
	# then
	assert response.status_code == 403
	assert response.json() == {"detail": "desktop-only"}
	assert prefs.picker_view_writes == []
	assert devices.device_calls == 0


def test_given_passcode_and_unauthenticated_lan_client_when_put_view_then_401_first() -> None:
	# given
	app, _devices, prefs = _app()
	passcode = NetworkPasscode(FakePasscodeStore(), FakePasscodeCrypto(), FakeClock())
	passcode.load()
	passcode.set_passcode("123456")
	app.state.services.network_passcode = passcode
	client = _lan(app)
	# when
	response = _put(client, {"path": "DCIM", "view": "grid"})
	# then
	assert response.status_code == 401
	assert response.json() == {"detail": "passcode-required"}
	assert prefs.picker_view_writes == []


# Settings -> Clear preferences


def test_given_stored_views_when_clear_preferences_then_views_empty_and_folder_resolves_by_type() -> None:
	# given
	app, devices, prefs = _app()
	devices.tree["DCIM/Camera"] = [DeviceEntry("a.jpg", False)]
	prefs.set_device_picker_view("DCIM/Camera", DeviceViewSetting.LIST)
	client = TestClient(app)
	# when
	response = client.post("/api/preferences/clear")
	# then
	assert response.status_code == 200
	assert dict(prefs.get_device_picker_views()) == {}
	data = client.post("/api/device/list", json=_body("DCIM/Camera")).json()
	assert data["stored_view"] is None
	assert data["folder_view"] == "grid"
