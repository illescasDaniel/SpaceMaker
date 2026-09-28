"""Desktop / phone web UI shell version (bump when static assets change materially).

Single source of truth: bump ``UI_SHELL_VERSION`` here only. Served HTML is stamped
at request time so ``app.js`` never hardcodes a parallel expected version.
"""

from __future__ import annotations

import hashlib
import os
import re


UI_SHELL_VERSION = "2026.09.processed-settings-uft"

_CSP_COMMON = (
	"default-src 'self'; "
	"style-src 'self' 'unsafe-inline'; "
	"font-src 'self'; "
	"img-src 'self' data: blob:; "
	"media-src 'self'; "
	"connect-src 'self' ws: wss:; "
	"base-uri 'self'; "
	"frame-ancestors 'none'; "
)

# LAN phone pages (upload/gallery QR): no eval.
CONTENT_SECURITY_POLICY = f"{_CSP_COMMON}script-src 'self' 'unsafe-inline'"

# Desktop pywebview (loopback): js_api bridge uses new Function() — requires unsafe-eval.
CONTENT_SECURITY_POLICY_DESKTOP = f"{_CSP_COMMON}script-src 'self' 'unsafe-inline' 'unsafe-eval'"

NO_CACHE_HEADERS = {"Cache-Control": "no-store, must-revalidate"}
# Long-lived browser cache for gallery thumbs and inline media (paths are content-stable until replaced).
MEDIA_CACHE_HEADERS = {"Cache-Control": "public, max-age=86400"}

# Thumbnails are cheap to re-fetch from the loopback server (the expensive step, on-disk
# generation, is already cached separately) but must never be trusted stale: a webview that
# cached a pre-fix or pre-reset thumbnail under `max-age=86400` would keep serving it for a day.
# `no-cache` still lets the client keep a copy, but it must revalidate via ETag first.
THUMB_CACHE_HEADERS = {"Cache-Control": "no-cache"}


def file_etag(stat_result: os.stat_result) -> str:
	"""Same weak-freshness ETag Starlette's FileResponse computes from mtime + size.

	Computed up front so a route can answer 304 on a client's ``If-None-Match`` without
	reading or serving the file body.
	"""
	basis = f"{stat_result.st_mtime}-{stat_result.st_size}"
	return f'"{hashlib.md5(basis.encode(), usedforsecurity=False).hexdigest()}"'


_SHELL_SCRIPT_RE = re.compile(
	r"<script>\s*window\.SPACEMAKER_SHELL\s*=\s*(\"(?:desktop|mobile_gallery)\");"
	r"(?:\s*window\.SPACEMAKER_UI_SHELL_VERSION\s*=\s*\"[^\"]*\";)?\s*</script>",
	re.IGNORECASE,
)
_APP_JS_SRC_RE = re.compile(r"/static/app\.js(?:\?[^\"']*)?")
_META_SHELL_RE = re.compile(
	r'<meta\s+name=["\']ui-shell-version["\']\s+content=["\'][^"\']*["\']\s*/?>',
	re.IGNORECASE,
)


def webengine_profile_slug() -> str:
	return UI_SHELL_VERSION.replace(".", "-")


def stamp_shell_html(html: str, *, version: str = UI_SHELL_VERSION) -> str:
	"""Embed ``version`` into shell HTML so the page matches ``/api/settings``.

	Rewrites the ``SPACEMAKER_SHELL`` bootstrap script, ``app.js?v=``, and a
	``ui-shell-version`` meta tag from the same constant used by the API.
	"""
	meta = f'<meta name="ui-shell-version" content="{version}">'
	if _META_SHELL_RE.search(html):
		html = _META_SHELL_RE.sub(meta, html, count=1)
	elif "<head>" in html:
		html = html.replace("<head>", f"<head>\n\t{meta}", 1)
	elif "<head " in html.lower():
		# Unusual capitalization / attributes — insert after first > of head tag.
		head_end = html.lower().find("<head")
		gt = html.find(">", head_end)
		if gt != -1:
			html = html[: gt + 1] + f"\n\t{meta}" + html[gt + 1 :]

	html = _SHELL_SCRIPT_RE.sub(
		rf'<script>window.SPACEMAKER_SHELL = \1; window.SPACEMAKER_UI_SHELL_VERSION = "{version}";</script>',
		html,
		count=1,
	)
	html = _APP_JS_SRC_RE.sub(f"/static/app.js?v={version}", html, count=1)
	return html
