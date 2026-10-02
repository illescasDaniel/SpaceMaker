from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from spacemaker.adapters.inbound.web.client_access import is_loopback_client_host
from spacemaker.adapters.inbound.web.media_paths import _STATIC
from spacemaker.adapters.inbound.web.routes.passcode import LOGIN_COOKIE
from spacemaker.application.network_passcode import NetworkPasscode


# The only paths a device without a login may reach: the unlock endpoint, the favicon, and the
# unlock page's own stylesheet and script (exact paths, never a prefix).
_EXEMPT_PATHS = frozenset({"/api/unlock", "/favicon.ico", "/static/unlock.css", "/static/js/unlock.js"})


def passcode_challenge(request: Request, passcode: NetworkPasscode | None) -> Response | None:
	"""None when the request may proceed; otherwise the 401 to send instead.

	Single enforcement point for the network passcode (spec: network-passcode):
	loopback is trusted, everything else needs the login cookie while a passcode is set.
	"""
	if passcode is None or not passcode.enabled:
		return None
	client_host = request.client.host if request.client else None
	if is_loopback_client_host(client_host):
		return None
	if request.url.path in _EXEMPT_PATHS:
		return None
	if passcode.is_login_valid(request.cookies.get(LOGIN_COOKIE)):
		return None
	wants_page = request.method == "GET" and "text/html" in request.headers.get("accept", "")
	if wants_page:
		return HTMLResponse(
			(_STATIC / "unlock.html").read_text(encoding="utf-8"),
			status_code=401,
			headers={"Cache-Control": "no-store"},
		)
	return JSONResponse({"detail": "passcode-required"}, status_code=401, headers={"Cache-Control": "no-store"})
