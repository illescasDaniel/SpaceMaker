from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from spacemaker.adapters.inbound.web.client_access import (
	is_loopback_client_host,
	require_loopback,
	require_loopback_websocket,
)


def test_given_loopback_hosts_when_is_loopback_then_true() -> None:
	assert is_loopback_client_host("127.0.0.1") is True
	assert is_loopback_client_host("::1") is True
	assert is_loopback_client_host("localhost") is True
	assert is_loopback_client_host("testclient") is True


def test_given_lan_host_when_is_loopback_then_false() -> None:
	assert is_loopback_client_host("10.0.0.2") is False
	assert is_loopback_client_host("192.168.1.50") is False


def _http_request(client_host: str | None) -> Request:
	scope = {
		"type": "http",
		"asgi": {"version": "3.0"},
		"http_version": "1.1",
		"method": "GET",
		"scheme": "http",
		"path": "/",
		"raw_path": b"/",
		"query_string": b"",
		"headers": [],
		"client": (client_host, 1234) if client_host else None,
		"server": ("127.0.0.1", 8765),
	}
	return Request(scope)


def test_given_loopback_client_when_require_loopback_then_ok() -> None:
	require_loopback(_http_request("127.0.0.1"))


def test_given_lan_client_when_require_loopback_then_403() -> None:
	with pytest.raises(HTTPException) as exc:
		require_loopback(_http_request("10.0.0.2"))
	assert exc.value.status_code == 403


class _WsClient:
	def __init__(self, host: str | None) -> None:
		self.host = host
		self.port = 1234


class _FakeWebSocket:
	def __init__(self, host: str | None) -> None:
		self.client = _WsClient(host) if host else None


def test_given_lan_websocket_when_require_loopback_websocket_then_false() -> None:
	assert require_loopback_websocket(_FakeWebSocket("10.0.0.2")) is False  # type: ignore[arg-type]
