from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from spacemaker.bootstrap.services import AppServices, repo_root
from spacemaker.bootstrap.ui_shell import NO_CACHE_HEADERS, stamp_shell_html
from spacemaker.domain.gallery_export import is_safe_gallery_relative_path
from spacemaker.domain.library import LibraryFolder


_STATIC = Path(__file__).resolve().parent / "static"
_LEGAL = {
	"privacy": repo_root() / "docs" / "legal" / "PRIVACY.md",
	"disclaimer": repo_root() / "docs" / "legal" / "DISCLAIMER.md",
	"third_party": repo_root() / "docs" / "legal" / "THIRD_PARTY_TOOLS.md",
}


def _path_is_under_base(base: Path, target: Path) -> bool:
	try:
		target.resolve().relative_to(base.resolve())
	except ValueError:
		return False
	return True


def _resolve_processed_file(services: AppServices, relative_path: str) -> Path:
	if not is_safe_gallery_relative_path(relative_path):
		raise HTTPException(status_code=403, detail="invalid path")
	root = services.session.library_root
	if not root:
		raise HTTPException(status_code=404)
	base = Path(services.filesystem.library_path(root, LibraryFolder.PROCESSED, "")).resolve()
	target = (base / relative_path).resolve()
	if not _path_is_under_base(base, target):
		raise HTTPException(status_code=403, detail="invalid path")
	if not target.is_file():
		raise HTTPException(status_code=404)
	return target


def _session_library_root(services: AppServices) -> str:
	return services.session.library_root


def _content_disposition(disposition: str, filename: str) -> str:
	"""``Content-Disposition`` safe for any filename.

	Header values must be latin-1, so non-ASCII names get an ASCII fallback plus an RFC 5987
	``filename*`` (UTF-8, percent-encoded); quotes, backslashes and control characters are dropped.
	"""
	clean = "".join(ch for ch in filename if ch not in '"\\' and ord(ch) >= 32 and ord(ch) != 127)
	ascii_name = clean.encode("ascii", "replace").decode("ascii").replace("?", "_") or "download"
	value = f'{disposition}; filename="{ascii_name}"'
	if clean and clean != ascii_name:
		value += f"; filename*=UTF-8''{quote(clean, safe='')}"
	return value


def _attachment_filename(path: Path) -> str:
	return _content_disposition("attachment", path.name)


def _attachment_named(filename: str) -> str:
	return _content_disposition("attachment", filename)


def _no_cache_file(path: Path) -> FileResponse:
	return FileResponse(path, headers=dict(NO_CACHE_HEADERS))


def _stamped_shell_page(path: Path) -> HTMLResponse:
	html = stamp_shell_html(path.read_text(encoding="utf-8"))
	return HTMLResponse(html, headers=dict(NO_CACHE_HEADERS))
