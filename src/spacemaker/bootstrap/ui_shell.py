"""Desktop / phone web UI shell asset token (auto, not hand-bumped).

Token is a short hash of ``static/js/*.js`` so HTML, ``/api/settings``, and an
import map stay in sync whenever the process starts. Shell HTML/CSS/JS are served
with ``Cache-Control: no-store`` — we do not rely on long-lived browser cache for
these lightweight pages. Qt WebEngine has still been observed to keep stale ES
module bytes for relative imports (``import "./api.js"``) that lack a ``?v=``;
``stamp_shell_html`` therefore emits an import map remapping every ``/static/js/*``
URL to the fingerprinted form.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path


def _static_js_dir() -> Path:
	return Path(__file__).resolve().parents[1] / "adapters" / "inbound" / "web" / "static" / "js"


def compute_ui_shell_version(*, js_dir: Path | None = None) -> str:
	"""Content fingerprint of shell ES modules (stable until those files change)."""
	root = js_dir if js_dir is not None else _static_js_dir()
	digest = hashlib.sha256()
	if root.is_dir():
		for path in sorted(root.glob("*.js")):
			digest.update(path.name.encode())
			digest.update(b"\0")
			digest.update(path.read_bytes())
			digest.update(b"\0")
	return digest.hexdigest()[:12]


# Computed once at import / process start — restart the app after rebuilding static/js.
UI_SHELL_VERSION = compute_ui_shell_version()

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
# Long-lived browser cache for inline /media/ previews (paths are content-stable until replaced).
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
_APP_JS_SRC_RE = re.compile(r"/static/(?:app\.js|js/[^\"'?]+)(?:\?[^\"']*)?")
_SHELL_CSS_HREF_RE = re.compile(
	r'((?:href)=["\'])(/static/(?:theme\.css|shell-[^\"\'?]+\.css))(?:\?[^\"\']*)?(["\'])',
	re.IGNORECASE,
)
_META_SHELL_RE = re.compile(
	r'<meta\s+name=["\']ui-shell-version["\']\s+content=["\'][^"\']*["\']\s*/?>',
	re.IGNORECASE,
)
_IMPORT_MAP_RE = re.compile(
	r'<script\s+type=["\']importmap["\']\s*>.*?</script>\s*',
	re.IGNORECASE | re.DOTALL,
)


def webengine_profile_slug() -> str:
	"""Fixed profile dir — shell assets are no-store + fingerprinted; no versioned cache escapes."""
	return "default"


def shell_js_import_map(*, version: str, js_dir: Path | None = None) -> str:
	"""Map absolute ``/static/js/*.js`` URLs to ``?v=`` forms so relative ES imports bust cache."""
	root = js_dir if js_dir is not None else _static_js_dir()
	imports: dict[str, str] = {}
	if root.is_dir():
		for path in sorted(root.glob("*.js")):
			url = f"/static/js/{path.name}"
			imports[url] = f"{url}?v={version}"
	return json.dumps({"imports": imports}, separators=(",", ":"))


def stamp_shell_html(
	html: str,
	*,
	version: str = UI_SHELL_VERSION,
	js_dir: Path | None = None,
) -> str:
	"""Embed ``version`` into shell HTML so the page matches ``/api/settings``.

	Rewrites the ``SPACEMAKER_SHELL`` bootstrap script, static JS/CSS ``?v=`` cache
	busters, a ``ui-shell-version`` meta tag, and an import map so every shell module
	URL (including relative imports) resolves to the fingerprinted form.
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

	def _stamp_js(match: re.Match[str]) -> str:
		path = match.group(0).split("?", 1)[0]
		return f"{path}?v={version}"

	html = _APP_JS_SRC_RE.sub(_stamp_js, html)
	html = _SHELL_CSS_HREF_RE.sub(rf"\1\2?v={version}\3", html)

	import_map = f'<script type="importmap">{shell_js_import_map(version=version, js_dir=js_dir)}</script>\n'
	html = _IMPORT_MAP_RE.sub("", html)
	# Import map must precede the module entry script.
	module_script = re.search(
		r'<script\s[^>]*type=["\']module["\'][^>]*>|<script\s[^>]*src="/static/js/main\.js',
		html,
		flags=re.IGNORECASE,
	)
	if module_script:
		html = html[: module_script.start()] + import_map + html[module_script.start() :]
	elif "</head>" in html.lower():
		idx = html.lower().rfind("</head>")
		html = html[:idx] + import_map + html[idx:]
	else:
		html = import_map + html
	return html
