import pytest

from spacemaker.adapters.inbound.web.lan_policy import is_lan_allowed


@pytest.mark.parametrize(
	("method", "path"),
	[
		("GET", "/gallery"),
		("GET", "/gallery/item/2024/a.avif"),
		("GET", "/upload"),
		("GET", "/upload/ended"),
		("GET", "/receive"),
		("GET", "/share"),
		("GET", "/transfer"),
		("HEAD", "/gallery"),
		("GET", "/static/js/main.js"),
		("GET", "/thumbs/a/b.jpg"),
		("GET", "/media/a/b.mp4"),
		("GET", "/api/gallery/timeline"),
		("GET", "/api/gallery/item/neighbor"),
		("DELETE", "/api/gallery/item"),
		("POST", "/api/gallery/batch/trash"),
		("GET", "/api/gallery/export/abc123/file"),
		("GET", "/api/upload/session"),
		("POST", "/api/upload"),
		("POST", "/api/receive"),
		("GET", "/api/share/download"),
		("POST", "/api/unlock"),
	],
)
def test_given_lan_endpoint_when_checked_then_allowed(method: str, path: str) -> None:
	# given / when / then
	assert is_lan_allowed(method, path)


@pytest.mark.parametrize(
	("method", "path"),
	[
		("GET", "/"),
		("POST", "/api/gallery/open"),
		("GET", "/api/server-info"),
		("GET", "/api/gallery/qr.svg"),
		("GET", "/api/legal/privacy"),
		("GET", "/json/version"),
		("POST", "/api/device/list"),
		("PUT", "/api/settings"),
		("GET", "/api/network-passcode"),
		("POST", "/api/usb-transfer/open-folder"),
		("POST", "/api/share/selection"),
		("GET", "/docs"),
		("GET", "/openapi.json"),
		("POST", "/gallery"),
		("GET", "/gallery-evil"),
		("GET", "/api/gallery/item/../settings"),
	],
)
def test_given_control_endpoint_when_checked_then_denied(method: str, path: str) -> None:
	# given / when / then
	assert not is_lan_allowed(method, path)
