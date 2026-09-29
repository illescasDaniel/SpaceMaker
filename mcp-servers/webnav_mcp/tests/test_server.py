"""Fast unit tests for webnav_mcp.server helpers (no live language servers)."""

from __future__ import annotations

from pathlib import Path

from webnav_mcp import server


def _write(path: Path, text: str = "") -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(text, encoding="utf-8")
	return path


def test_given_no_jsconfig_when_js_files_fallback_then_finds_js_files(tmp_path, monkeypatch):
	# given — no jsconfig.json, so `_js_include_globs` returns nothing; the
	# fallback scan should still find the project's own JS files.
	_write(tmp_path / "app.js")
	_write(tmp_path / "lib" / "util.mjs")
	monkeypatch.setattr(server, "WEB_ROOTS", None)
	# when
	files = server._js_files_fallback(tmp_path)
	# then
	assert {p.name for p in files} == {"app.js", "util.mjs"}


def test_given_venv_and_node_modules_when_js_files_fallback_then_excludes_them(tmp_path, monkeypatch):
	# given
	_write(tmp_path / "app.js")
	_write(tmp_path / "node_modules" / "pkg" / "index.js")
	_write(tmp_path / ".venv" / "lib" / "vendored.js")
	monkeypatch.setattr(server, "WEB_ROOTS", None)
	# when
	files = server._js_files_fallback(tmp_path)
	# then
	assert {p.name for p in files} == {"app.js"}


def test_given_configured_web_roots_when_js_files_fallback_then_scans_only_those_roots(tmp_path, monkeypatch):
	# given
	web_root = tmp_path / "web"
	other_root = tmp_path / "other"
	_write(web_root / "app.js")
	_write(other_root / "ignored.js")
	monkeypatch.setattr(server, "WEB_ROOTS", [("web", web_root)])
	# when
	files = server._js_files_fallback(tmp_path)
	# then
	assert {p.name for p in files} == {"app.js"}
