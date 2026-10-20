# Video posters, HTTP surface (SPEC "Video posters — API").
# Seams for Phase 4:
#   ``AppServices.read_device_stream`` is a callable ``(token: str, range_header: str | None) -> DeviceStreamChunk``
#   (the ``ReadDeviceStream`` use case) raising ``DeviceStreamError`` / ``DevicePreviewError``; the route
#   forwards the ``token`` query value and the raw ``Range`` header (``None`` when absent).
#   ``DeviceStreamError(RANGE_NOT_SATISFIABLE).detail`` is the file size, rendered as ``Content-Range: bytes */<size>``.
#   ``GET /api/device/thumb|preview`` add ``X-Media-Duration: <seconds>`` (``str(float)``) when ``DevicePreview.duration_s``
#   is set, on 200 and on 304, and omit it otherwise.
# Mapping: 206 chunk / 400 range_required / 403 desktop-only / 404 unknown_token / 409 device_busy /
#   416 range_not_satisfiable / 503 unplugged|timeout|unauthorized; the stream route is not in LAN_ALLOWED_ROUTES.
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
from spacemaker.domain.device_preview import (
	STREAM_MAX_CHUNK_BYTES,
	DevicePreview,
	DevicePreviewCancelled,
	DevicePreviewError,
	DevicePreviewErrorKind,
	DevicePreviewRequest,
)
from spacemaker.domain.device_stream import DeviceStreamChunk, DeviceStreamError, DeviceStreamErrorKind


PHONE = ("192.168.1.50", 50000)
ETAG = '"vid123"'
JPEG = b"\xff\xd8\xff-fake-poster"
QUERY = {
	"method": "adb",
	"device_id": "dev1",
	"path": "DCIM/Camera/VID_0001.mp4",
	"size": 90000000,
	"mtime": 1700000000,
}
TOKEN = "tok_ABC-123"  # noqa: S105 - fake stream token
DATA = b"x" * 100


class _StubGetDevicePreview:
	def __init__(self) -> None:
		self.duration_s: float | None = 42.37
		self.error: DevicePreviewErrorKind | None = None
		self.cancel_error = False
		self.cancels: list[threading.Event | None] = []

	def __call__(self, request: DevicePreviewRequest, *, cancel: threading.Event | None = None) -> DevicePreview:
		self.cancels.append(cancel)
		if self.cancel_error:
			raise DevicePreviewCancelled
		if self.error is not None:
			raise DevicePreviewError(self.error)
		return DevicePreview(JPEG, ETAG, self.duration_s)


class _StubReadDeviceStream:
	def __init__(self) -> None:
		self.calls: list[tuple[str, str | None]] = []
		self.chunk = DeviceStreamChunk(DATA, 100, 199, 1000)
		self.error: Exception | None = None

	def __call__(self, token: str, range_header: str | None) -> DeviceStreamChunk:
		self.calls.append((token, range_header))
		if self.error is not None:
			raise self.error
		return self.chunk


class _StubServices(AppServices):
	def __init__(
		self, library_root: str, get_device_preview: _StubGetDevicePreview, read_device_stream: _StubReadDeviceStream
	) -> None:
		self.session = AppSession(library_root=library_root)
		self.filesystem = LocalFileSystem()
		self.get_device_preview = get_device_preview
		self.read_device_stream = read_device_stream

	def shutdown(self, *, timeout_seconds: float = 10.0) -> None:
		pass


@pytest.fixture
def preview() -> _StubGetDevicePreview:
	return _StubGetDevicePreview()


@pytest.fixture
def stream() -> _StubReadDeviceStream:
	return _StubReadDeviceStream()


@pytest.fixture
def desktop(tmp_path: Path, preview: _StubGetDevicePreview, stream: _StubReadDeviceStream) -> Iterator[TestClient]:
	with TestClient(create_fastapi_app(_StubServices(str(tmp_path), preview, stream))) as client:
		yield client


@pytest.fixture
def phone(tmp_path: Path, preview: _StubGetDevicePreview, stream: _StubReadDeviceStream) -> Iterator[TestClient]:
	with TestClient(create_fastapi_app(_StubServices(str(tmp_path), preview, stream)), client=PHONE) as client:
		yield client


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_video_with_duration_when_get_then_200_with_media_duration_header(
	desktop: TestClient, route: str
) -> None:
	# given
	# when
	response = desktop.get(route, params=QUERY)
	# then
	assert response.status_code == 200
	assert response.headers["x-media-duration"] == "42.37"
	assert response.content == JPEG


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_video_with_duration_when_matching_if_none_match_then_304_still_has_media_duration(
	desktop: TestClient, route: str
) -> None:
	# given
	headers = {"If-None-Match": ETAG}
	# when
	response = desktop.get(route, params=QUERY, headers=headers)
	# then
	assert response.status_code == 304
	assert response.headers["x-media-duration"] == "42.37"
	assert response.headers["etag"] == ETAG


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_unknown_duration_when_get_then_header_omitted_on_200_and_304(
	desktop: TestClient, preview: _StubGetDevicePreview, route: str
) -> None:
	# given
	preview.duration_s = None
	# when
	ok = desktop.get(route, params=QUERY)
	not_modified = desktop.get(route, params=QUERY, headers={"If-None-Match": ETAG})
	# then
	assert ok.status_code == 200
	assert "x-media-duration" not in ok.headers
	assert not_modified.status_code == 304
	assert "x-media-duration" not in not_modified.headers


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_failure_when_get_video_then_no_media_duration_header(
	desktop: TestClient, preview: _StubGetDevicePreview, route: str
) -> None:
	# given
	preview.error = DevicePreviewErrorKind.DEVICE_BUSY
	# when
	response = desktop.get(route, params=QUERY)
	# then
	assert response.status_code == 409
	assert "x-media-duration" not in response.headers


def test_given_range_when_get_stream_then_206_with_content_range_and_octet_stream(
	desktop: TestClient, stream: _StubReadDeviceStream
) -> None:
	# given
	headers = {"Range": "bytes=100-199"}
	# when
	response = desktop.get("/api/device/stream", params={"token": TOKEN}, headers=headers)
	# then
	assert response.status_code == 206
	assert response.content == DATA
	assert response.headers["content-range"] == "bytes 100-199/1000"
	assert response.headers["accept-ranges"] == "bytes"
	assert response.headers["content-type"] == "application/octet-stream"
	assert response.headers["content-length"] == "100"
	assert stream.calls == [(TOKEN, "bytes=100-199")]


def test_given_truncated_chunk_when_get_stream_then_content_range_states_bytes_actually_sent(
	desktop: TestClient, stream: _StubReadDeviceStream
) -> None:
	# given
	big = b"y" * STREAM_MAX_CHUNK_BYTES
	stream.chunk = DeviceStreamChunk(big, 0, STREAM_MAX_CHUNK_BYTES - 1, 100 * STREAM_MAX_CHUNK_BYTES)
	# when
	response = desktop.get("/api/device/stream", params={"token": TOKEN}, headers={"Range": "bytes=0-"})
	# then
	assert response.status_code == 206
	assert len(response.content) == STREAM_MAX_CHUNK_BYTES
	assert response.headers["content-range"] == f"bytes 0-{STREAM_MAX_CHUNK_BYTES - 1}/{100 * STREAM_MAX_CHUNK_BYTES}"


def test_given_no_range_header_when_get_stream_then_forwarded_as_none_and_400_range_required(
	desktop: TestClient, stream: _StubReadDeviceStream
) -> None:
	# given
	stream.error = DeviceStreamError(DeviceStreamErrorKind.RANGE_REQUIRED)
	# when
	response = desktop.get("/api/device/stream", params={"token": TOKEN})
	# then
	assert stream.calls == [(TOKEN, None)]
	assert response.status_code == 400
	assert response.json() == {"detail": "range_required"}


def test_given_range_past_size_when_get_stream_then_416_with_unsatisfied_content_range(
	desktop: TestClient, stream: _StubReadDeviceStream
) -> None:
	# given
	stream.error = DeviceStreamError(DeviceStreamErrorKind.RANGE_NOT_SATISFIABLE, "1000")
	# when
	response = desktop.get("/api/device/stream", params={"token": TOKEN}, headers={"Range": "bytes=5000-"})
	# then
	assert response.status_code == 416
	assert response.json() == {"detail": "range_not_satisfiable"}
	assert response.headers["content-range"] == "bytes */1000"


def test_given_unknown_token_when_get_stream_then_404_unknown_token(
	desktop: TestClient, stream: _StubReadDeviceStream
) -> None:
	# given
	stream.error = DeviceStreamError(DeviceStreamErrorKind.UNKNOWN_TOKEN)
	# when
	response = desktop.get("/api/device/stream", params={"token": "nope"}, headers={"Range": "bytes=0-9"})
	# then
	assert response.status_code == 404
	assert response.json() == {"detail": "unknown_token"}


@pytest.mark.parametrize(
	("error", "status"),
	[
		(DevicePreviewErrorKind.DEVICE_BUSY, 409),
		(DevicePreviewErrorKind.UNPLUGGED, 503),
		(DevicePreviewErrorKind.TIMEOUT, 503),
		(DevicePreviewErrorKind.UNAUTHORIZED, 503),
	],
)
def test_given_device_error_when_get_stream_then_status_and_detail_code(
	desktop: TestClient, stream: _StubReadDeviceStream, error: DevicePreviewErrorKind, status: int
) -> None:
	# given
	stream.error = DevicePreviewError(error)
	# when
	response = desktop.get("/api/device/stream", params={"token": TOKEN}, headers={"Range": "bytes=0-9"})
	# then
	assert response.status_code == status
	assert response.json() == {"detail": error.value}


def test_given_lan_client_when_get_stream_then_403_desktop_only_and_use_case_not_called(
	phone: TestClient, stream: _StubReadDeviceStream
) -> None:
	# given
	# when
	response = phone.get("/api/device/stream", params={"token": TOKEN}, headers={"Range": "bytes=0-9"})
	# then
	assert response.status_code == 403
	assert response.json() == {"detail": "desktop-only"}
	assert stream.calls == []


def test_given_stream_route_when_checked_against_lan_policy_then_not_allowed() -> None:
	# given
	# when
	allowed = is_lan_allowed("GET", "/api/device/stream")
	# then
	assert allowed is False


@pytest.mark.parametrize("route", ["/api/device/thumb", "/api/device/preview"])
def test_given_request_when_get_then_use_case_receives_an_unset_cancel_event(
	desktop: TestClient, preview: _StubGetDevicePreview, route: str
) -> None:
	# given
	# when
	desktop.get(route, params=QUERY)
	# then
	assert len(preview.cancels) == 1
	assert isinstance(preview.cancels[0], threading.Event)
	assert not preview.cancels[0].is_set()


def test_given_use_case_cancelled_when_get_thumb_then_499_without_body(
	desktop: TestClient, preview: _StubGetDevicePreview
) -> None:
	# given
	preview.cancel_error = True
	# when
	response = desktop.get("/api/device/thumb", params=QUERY)
	# then
	assert response.status_code == 499
	assert response.content == b""


class _DisconnectedRequest:
	"""Stands in for a Starlette request whose client has already gone."""

	async def is_disconnected(self) -> bool:
		return True


def test_given_client_disconnects_when_running_preview_work_then_cancel_event_is_set() -> None:
	# given
	import anyio

	from spacemaker.adapters.inbound.web.routes.device import _run_until_disconnect

	def work(cancel: threading.Event) -> bool:
		return cancel.wait(timeout=5.0)  # returns as soon as the watcher sets the event

	# when
	seen = anyio.run(_run_until_disconnect, _DisconnectedRequest(), work)
	# then
	assert seen is True
