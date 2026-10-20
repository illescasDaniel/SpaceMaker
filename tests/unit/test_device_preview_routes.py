# Expected seam for Phase 4: ``AppServices.get_device_preview`` is a callable
# ``(DevicePreviewRequest) -> DevicePreview`` (the ``GetDevicePreview`` use case) that raises ``DevicePreviewError``.
# Routes: ``GET /api/device/thumb`` and ``GET /api/device/preview``, loopback-only, not in ``LAN_ALLOWED_ROUTES``.
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from spacemaker.adapters.inbound.web.app import create_fastapi_app
from spacemaker.adapters.inbound.web.lan_policy import is_lan_allowed
from spacemaker.adapters.inbound.web.session import AppSession
from spacemaker.adapters.outbound.filesystem.local import LocalFileSystem
from spacemaker.bootstrap.services import AppServices
from spacemaker.domain.connection import ConnectionMethod
from spacemaker.domain.device_preview import (
	DevicePreview,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewKind,
	DevicePreviewRequest,
)


PHONE = ("192.168.1.50", 50000)
ETAG = '"abc123"'
JPEG = b"\xff\xd8\xff-fake-jpeg"
QUERY = {"method": "adb", "device_id": "dev1", "path": "DCIM/Camera/IMG_0001.jpg", "size": 800000, "mtime": 1700000000}


class _StubGetDevicePreview:
	def __init__(self, error: DevicePreviewErrorKind | None = None) -> None:
		self.error = error
		self.requests: list[DevicePreviewRequest] = []
		self.cancels: list[threading.Event | None] = []

	def __call__(self, request: DevicePreviewRequest, *, cancel: threading.Event | None = None) -> DevicePreview:
		self.cancels.append(cancel)
		self.requests.append(request)
		if self.error is not None:
			raise DevicePreviewError(self.error)
		return DevicePreview(JPEG, ETAG)


class _StubServices(AppServices):
	def __init__(self, library_root: str, get_device_preview: _StubGetDevicePreview) -> None:
		self.session = AppSession(library_root=library_root)
		self.filesystem = LocalFileSystem()
		self.get_device_preview = get_device_preview

	def shutdown(self, *, timeout_seconds: float = 10.0) -> None:
		pass


@pytest.fixture
def use_case() -> _StubGetDevicePreview:
	return _StubGetDevicePreview()


@pytest.fixture
def desktop(tmp_path: Path, use_case: _StubGetDevicePreview) -> Iterator[TestClient]:
	with TestClient(create_fastapi_app(_StubServices(str(tmp_path), use_case))) as client:
		yield client


@pytest.fixture
def phone(tmp_path: Path, use_case: _StubGetDevicePreview) -> Iterator[TestClient]:
	with TestClient(create_fastapi_app(_StubServices(str(tmp_path), use_case)), client=PHONE) as client:
		yield client


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_success_when_get_then_jpeg_with_strong_etag_and_private_cache_headers(
	desktop: TestClient, use_case: _StubGetDevicePreview, route: str
) -> None:
	# given
	# when
	response = desktop.get(route, params=QUERY)
	# then
	assert response.status_code == 200
	assert response.headers["content-type"] == "image/jpeg"
	assert response.content == JPEG
	assert response.headers["etag"] == ETAG
	assert response.headers["cache-control"] == "private, max-age=300, must-revalidate"
	assert len(use_case.requests) == 1


@pytest.mark.parametrize(
	("route", "kind"),
	[("/api/device/thumb", DevicePreviewKind.THUMB), ("/api/device/preview", DevicePreviewKind.PREVIEW)],
)
def test_given_query_when_get_then_use_case_receives_typed_request(
	desktop: TestClient, use_case: _StubGetDevicePreview, route: str, kind: DevicePreviewKind
) -> None:
	# given
	# when
	desktop.get(route, params=QUERY)
	# then
	assert use_case.requests == [
		DevicePreviewRequest(ConnectionMethod.ADB, "dev1", "DCIM/Camera/IMG_0001.jpg", 800000, 1700000000, kind)
	]


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_matching_if_none_match_when_get_then_304_without_body(desktop: TestClient, route: str) -> None:
	# given
	headers = {"If-None-Match": ETAG}
	# when
	response = desktop.get(route, params=QUERY, headers=headers)
	# then
	assert response.status_code == 304
	assert response.content == b""
	assert response.headers["etag"] == ETAG
	assert response.headers["cache-control"] == "private, max-age=300, must-revalidate"


def test_given_other_if_none_match_when_get_then_200_with_body(desktop: TestClient) -> None:
	# given
	headers = {"If-None-Match": '"stale"'}
	# when
	response = desktop.get("/api/device/thumb", params=QUERY, headers=headers)
	# then
	assert response.status_code == 200
	assert response.content == JPEG


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
@pytest.mark.parametrize(
	("error", "status"),
	[
		(DevicePreviewErrorKind.INVALID_PATH, 400),
		(DevicePreviewErrorKind.NO_PREVIEW, 404),
		(DevicePreviewErrorKind.DEVICE_BUSY, 409),
		(DevicePreviewErrorKind.TOO_LARGE, 413),
		(DevicePreviewErrorKind.UNPLUGGED, 503),
		(DevicePreviewErrorKind.TIMEOUT, 503),
		(DevicePreviewErrorKind.UNAUTHORIZED, 503),
	],
)
def test_given_use_case_error_when_get_then_status_and_detail_code(
	desktop: TestClient, use_case: _StubGetDevicePreview, route: str, error: DevicePreviewErrorKind, status: int
) -> None:
	# given
	use_case.error = error
	# when
	response = desktop.get(route, params=QUERY)
	# then
	assert response.status_code == status
	assert response.json() == {"detail": error.value}
	assert "etag" not in response.headers


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
@pytest.mark.parametrize(
	"params",
	[
		{"method": "adb", "device_id": "dev1", "path": "a.jpg", "mtime": 1},
		{"method": "adb", "device_id": "dev1", "path": "a.jpg", "size": 1},
		{"method": "adb", "device_id": "dev1", "path": "a.jpg", "size": -1, "mtime": 1},
		{"method": "adb", "device_id": "dev1", "path": "a.jpg", "size": 1, "mtime": -1},
		{"method": "adb", "device_id": "dev1", "path": "a.jpg", "size": "big", "mtime": 1},
	],
)
def test_given_missing_or_negative_size_or_mtime_when_get_then_422_and_use_case_not_called(
	desktop: TestClient, use_case: _StubGetDevicePreview, route: str, params: dict[str, object]
) -> None:
	# given
	# when
	response = desktop.get(route, params=params)  # type: ignore[arg-type]
	# then
	assert response.status_code == 422
	assert use_case.requests == []


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
@pytest.mark.parametrize(
	"change",
	[{"method": "bluetooth"}, {"method": "wifi"}, {"device_id": ""}, {"device_id": "   "}],
)
def test_given_unknown_method_or_empty_device_when_get_then_400_invalid_path_and_use_case_not_called(
	desktop: TestClient, use_case: _StubGetDevicePreview, route: str, change: dict[str, object]
) -> None:
	# given
	params = {**QUERY, **change}
	# when
	response = desktop.get(route, params=params)  # type: ignore[arg-type]
	# then
	assert response.status_code == 400
	assert response.json() == {"detail": "invalid_path"}
	assert use_case.requests == []


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_lan_client_when_get_then_403_desktop_only_and_use_case_not_called(
	phone: TestClient, use_case: _StubGetDevicePreview, route: str
) -> None:
	# given
	# when
	response = phone.get(route, params=QUERY)
	# then
	assert response.status_code == 403
	assert response.json() == {"detail": "desktop-only"}
	assert use_case.requests == []


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_preview_route_when_checked_against_lan_policy_then_not_allowed(route: str) -> None:
	# given
	# when
	allowed = is_lan_allowed("GET", route)
	# then
	assert allowed is False
