"""Fast unit tests for webnav_mcp.server helpers (no live language servers)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp_nav_shared.errors import ToolInputError
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


@pytest.mark.parametrize("name", ["a.ts", "a.mts", "a.cts", "a.js"])
def test_given_script_file_when_client_for_then_routes_to_ts_server(monkeypatch, name):
	# given
	sentinel = object()

	async def _fake_ts_client() -> object:
		return sentinel

	monkeypatch.setattr(server, "_get_ts_client", _fake_ts_client)
	# when
	client = asyncio.run(server._client_for(name))
	# then
	assert client is sentinel


def test_given_ts_and_js_when_language_ids_then_ts_is_typescript():
	# then
	assert server._SCRIPT_LANGUAGE_IDS[".ts"] == "typescript"
	assert server._SCRIPT_LANGUAGE_IDS[".js"] == "javascript"


def test_given_ts_file_when_js_files_fallback_then_includes_ts(tmp_path, monkeypatch):
	# given
	_write(tmp_path / "app.ts")
	monkeypatch.setattr(server, "WEB_ROOTS", [])
	# when
	files = server._js_files_fallback(tmp_path)
	# then
	assert {p.name for p in files} == {"app.ts"}


def test_given_generated_dir_when_client_for_script_then_rejected_with_source_hint(tmp_path, monkeypatch):
	# given
	out = tmp_path / "static" / "js"
	monkeypatch.setattr(server, "WORKSPACE_ROOT", tmp_path)
	monkeypatch.setattr(server, "GENERATED_PATHS", [out.resolve()])
	# when / then
	with pytest.raises(ToolInputError, match="generated output"):
		asyncio.run(server._client_for(str(out / "dom.js")))


def test_given_generated_dir_when_is_generated_then_only_paths_under_it_match(tmp_path, monkeypatch):
	# given
	out = tmp_path / "static" / "js"
	monkeypatch.setattr(server, "GENERATED_PATHS", [out.resolve()])
	# when / then
	assert server._is_generated(out / "dom.js")
	assert server._is_generated(out)
	assert not server._is_generated(tmp_path / "static" / "other.js")
	assert not server._is_generated(tmp_path / "web" / "dom.ts")


def test_given_symbols_in_generated_and_source_when_search_symbol_then_only_source_listed(tmp_path, monkeypatch):
	# given
	out = tmp_path / "static" / "js"
	monkeypatch.setattr(server, "WORKSPACE_ROOT", tmp_path)
	monkeypatch.setattr(server, "GENERATED_PATHS", [out.resolve()])

	def _sym(path: Path) -> dict:
		pos = {"line": 0, "character": 0}
		return {
			"name": "isDesktopShell",
			"kind": 12,
			"location": {"uri": path.as_uri(), "range": {"start": pos, "end": pos}},
		}

	class _FakeClient:
		async def workspace_symbol(self, _query: str) -> list[dict]:
			return [_sym(tmp_path / "web" / "dom.ts"), _sym(out / "dom.js")]

	async def _fake_ts_client() -> _FakeClient:
		return _FakeClient()

	monkeypatch.setattr(server, "_get_ts_client", _fake_ts_client)
	# when
	result = asyncio.run(server.search_symbol("isDesktopShell"))
	# then
	assert "dom.ts" in result
	assert "dom.js" not in result


def test_given_query_alias_when_selector_called_then_behaves_like_name(monkeypatch):
	# given
	seen: list[str] = []
	monkeypatch.setattr(server.web_index, "build_workspace_index", lambda *_: [])
	monkeypatch.setattr(server.web_index, "format_selector", lambda _idx, name, **_kw: seen.append(name) or "ok")
	# when
	result = asyncio.run(server.selector(query=".thumb-removing"))
	# then
	assert result == "ok"
	assert seen == [".thumb-removing"]


def test_given_query_alias_when_css_var_called_then_behaves_like_name(monkeypatch):
	# given
	seen: list[str] = []
	monkeypatch.setattr(server.web_index, "build_workspace_index", lambda *_: [])
	monkeypatch.setattr(server.web_index, "format_css_var", lambda _idx, name, **_kw: seen.append(name) or "ok")
	# when
	result = asyncio.run(server.css_var(query="--bg"))
	# then
	assert result == "ok"
	assert seen == ["--bg"]


def test_given_neither_name_nor_query_when_selector_called_then_returns_actionable_error():
	# when
	result = asyncio.run(server.selector())
	# then
	assert "name" in result
