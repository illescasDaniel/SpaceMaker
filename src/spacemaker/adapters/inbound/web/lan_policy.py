from __future__ import annotations

import re
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response


@dataclass(frozen=True)
class LanRoute:
	"""One route a non-loopback client may reach. ``pattern`` is matched against the whole path."""

	method: str
	pattern: re.Pattern[str]


def _route(method: str, pattern: str) -> LanRoute:
	return LanRoute(method, re.compile(pattern))


# Default-deny: a non-loopback request that matches nothing here is answered 403 `desktop-only`.
# Mirrors the route table in specs/lan-access/SPEC.md (keep both in sync; the route-audit test enforces it).
LAN_ALLOWED_ROUTES: tuple[LanRoute, ...] = (
	_route("GET", r"/gallery(/item/.*)?"),
	_route("GET", r"/(upload|upload/ended|receive|share|transfer)"),
	_route("GET", r"/favicon\.ico"),
	_route("GET", r"/static/.*"),
	_route("GET", r"/(thumbs|media)/.*"),
	_route("GET", r"/api/gallery/(timeline|calendar|item|day|item/neighbor)"),
	_route("DELETE", r"/api/gallery/item"),
	_route("POST", r"/api/gallery/(export|batch/trash|batch/convert|batch/download)"),
	_route("GET", r"/api/gallery/(export|batch/convert)/[^/]+(/file)?"),
	_route("GET", r"/api/(upload|receive|share|transfer)/session"),
	_route("POST", r"/api/(upload|receive|transfer)"),
	_route("GET", r"/api/(share|transfer)/download"),
	_route("POST", r"/api/unlock"),
)

# `GET /` from a non-loopback client is served the notice page (wireframes/phone-desktop-only.html), not the app.
LAN_NOTICE_PATH = "/"


def is_lan_allowed(method: str, path: str) -> bool:
	"""True when a non-loopback client may call ``method path`` (see LAN_ALLOWED_ROUTES)."""
	raise NotImplementedError


def lan_policy_challenge(request: Request) -> Response | None:
	"""None when the request may proceed; otherwise the 403 `desktop-only` (or the notice page for `GET /`)."""
	raise NotImplementedError
