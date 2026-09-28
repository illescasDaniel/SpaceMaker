"""Fast unit tests for codenav/webnav shared MCP helpers (no live language servers)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest


_MCP_ROOT = Path(__file__).resolve().parents[2] / "mcp-servers"
if str(_MCP_ROOT) not in sys.path:
	sys.path.insert(0, str(_MCP_ROOT))

from _shared.errors import TOOL_ERRORS, ToolInputError, format_tool_error  # noqa: E402
from _shared.format import (  # noqa: E402
	format_location,
	format_workspace_symbol,
	format_workspace_symbols,
	rank_workspace_symbols,
	uri_to_relative,
	workspace_symbol_position,
)
from _shared.lsp_client import LanguageServerExitedError, LspClient, LspRequestError  # noqa: E402
from _shared.workspace import resolve_workspace_root  # noqa: E402


def test_given_location_when_format_then_header_includes_line_and_column(tmp_path):
	# given
	src = tmp_path / "pkg" / "mod.py"
	src.parent.mkdir()
	src.write_text("\n\nclass Foo:\n\tpass\n", encoding="utf-8")
	loc = {
		"uri": src.as_uri(),
		"range": {
			"start": {"line": 2, "character": 6},
			"end": {"line": 2, "character": 9},
		},
	}
	# when
	text = format_location(loc, tmp_path)
	# then
	assert text.splitlines()[0] == "pkg/mod.py:3:7"
	assert "class Foo:" in text


def test_given_location_link_when_format_then_prefers_selection_range(tmp_path):
	# given
	src = tmp_path / "a.py"
	src.write_text("x = 1\n", encoding="utf-8")
	loc = {
		"targetUri": src.as_uri(),
		"targetRange": {
			"start": {"line": 0, "character": 0},
			"end": {"line": 0, "character": 5},
		},
		"targetSelectionRange": {
			"start": {"line": 0, "character": 0},
			"end": {"line": 0, "character": 1},
		},
	}
	# when
	header = format_location(loc, tmp_path).splitlines()[0]
	# then
	assert header == "a.py:1:1"


def test_given_uri_under_workspace_when_uri_to_relative_then_uses_forward_slashes(tmp_path):
	# given
	nested = tmp_path / "src" / "pkg" / "x.py"
	nested.parent.mkdir(parents=True)
	nested.write_text("pass\n", encoding="utf-8")
	# when / then
	assert uri_to_relative(nested.as_uri(), tmp_path) == "src/pkg/x.py"


def test_given_explicit_env_when_resolve_workspace_root_then_prefers_it(tmp_path, monkeypatch):
	# given
	override = tmp_path / "override"
	override.mkdir()
	fallback = tmp_path / "fallback"
	fallback.mkdir()
	monkeypatch.setenv("CODENAV_MCP_WORKSPACE", str(override))
	monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(fallback))
	# when
	root = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
	# then
	assert root == override.resolve()


def test_given_claude_project_dir_when_no_explicit_env_then_uses_claude(tmp_path, monkeypatch):
	# given
	claude = tmp_path / "claude-root"
	claude.mkdir()
	monkeypatch.delenv("CODENAV_MCP_WORKSPACE", raising=False)
	monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude))
	# when
	root = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
	# then
	assert root == claude.resolve()


def test_given_no_env_when_resolve_workspace_root_then_repo_from_package(monkeypatch):
	# given
	monkeypatch.delenv("CODENAV_MCP_WORKSPACE", raising=False)
	monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
	# when
	root = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
	# then — mcp-servers/_shared/workspace.py → three parents = repo root
	assert (root / "mcp-servers" / "_shared" / "workspace.py").is_file()


def test_given_message_when_lsp_request_error_then_exposes_method():
	# given / when
	err = LspRequestError("textDocument/hover", -32601, "Method not found")
	# then
	assert err.method == "textDocument/hover"
	assert err.code == -32601
	assert "Method not found" in str(err)


class _FakeStdin:
	def write(self, _data: bytes) -> None:
		return None

	async def drain(self) -> None:
		return None


class _FakeProc:
	stdin = _FakeStdin()


def _started_client(tmp_path: Path, *, language_id: str = "python") -> LspClient:
	client = LspClient(workspace_root=tmp_path, command=["true"], language_id=language_id)
	client._started = True
	client._proc = _FakeProc()  # type: ignore[assignment]
	return client


def test_given_jsonrpc_error_when_request_then_raises_lsp_request_error(tmp_path):
	# given
	client = _started_client(tmp_path)

	async def _run() -> None:
		async def _respond() -> None:
			await asyncio.sleep(0)
			msg_id = next(iter(client._pending))
			client._dispatch(
				{
					"jsonrpc": "2.0",
					"id": msg_id,
					"error": {"code": -32601, "message": "Method not found"},
				}
			)

		task = asyncio.create_task(_respond())
		with pytest.raises(LspRequestError) as caught:
			await client._request("textDocument/hover", {})
		await task
		assert caught.value.method == "textDocument/hover"
		assert "Method not found" in str(caught.value)

	# when / then
	asyncio.run(_run())


def test_given_pull_unsupported_when_diagnostics_then_returns_push_cache(tmp_path, monkeypatch):
	# given
	src = tmp_path / "x.css"
	src.write_text("a {}\n", encoding="utf-8")
	client = _started_client(tmp_path, language_id="css")
	uri = src.resolve().as_uri()
	cached = [{"message": "from push", "range": {"start": {"line": 0, "character": 0}}}]
	client._diagnostics[uri] = cached

	async def _boom(_method: str, _params: dict, timeout: float = 20) -> dict:
		raise LspRequestError("textDocument/diagnostic", -32601, "Method not found")

	monkeypatch.setattr(client, "_request", _boom)
	# when
	items = asyncio.run(client.diagnostics(str(src)))
	# then
	assert items == cached


def test_given_empty_pull_and_push_cache_when_diagnostics_then_prefers_cache(tmp_path, monkeypatch):
	# given
	src = tmp_path / "x.html"
	src.write_text("<p></p>\n", encoding="utf-8")
	client = _started_client(tmp_path, language_id="html")
	uri = src.resolve().as_uri()
	cached = [{"message": "pushed", "range": {"start": {"line": 0, "character": 0}}}]
	client._diagnostics[uri] = cached

	async def _empty(_method: str, _params: dict, timeout: float = 20) -> dict:
		return {"result": {"kind": "full", "items": []}}

	monkeypatch.setattr(client, "_request", _empty)
	# when
	items = asyncio.run(client.diagnostics(str(src)))
	# then
	assert items == cached


def test_given_class_keyword_range_when_format_workspace_symbol_then_column_on_name(tmp_path):
	# given — ty-style SymbolInformation range starts at `class`
	src = tmp_path / "mod.py"
	src.write_text("class Foo:\n\tpass\n", encoding="utf-8")
	sym = {
		"name": "Foo",
		"kind": 5,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 0, "character": 9},
			},
		},
	}
	# when
	line = format_workspace_symbol(sym, tmp_path)
	uri, row, col = workspace_symbol_position(sym)
	# then
	assert line == "Foo  [Class]  (mod.py:1:7)"
	assert uri == src.as_uri()
	assert (row, col) == (0, 6)


def test_given_selection_range_when_workspace_symbol_position_then_uses_it(tmp_path):
	# given
	src = tmp_path / "a.py"
	src.write_text("class Bar:\n\tpass\n", encoding="utf-8")
	sym = {
		"name": "Bar",
		"kind": 5,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 1, "character": 5},
			},
		},
		"selectionRange": {
			"start": {"line": 0, "character": 6},
			"end": {"line": 0, "character": 9},
		},
	}
	# when
	_uri, row, col = workspace_symbol_position(sym)
	# then
	assert (row, col) == (0, 6)


def test_given_name_missing_from_line_when_workspace_symbol_position_then_range_start(tmp_path):
	# given
	src = tmp_path / "a.py"
	src.write_text("x = 1\n", encoding="utf-8")
	sym = {
		"name": "Missing",
		"kind": 13,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 2},
				"end": {"line": 0, "character": 3},
			},
		},
	}
	# when
	_uri, row, col = workspace_symbol_position(sym)
	# then
	assert (row, col) == (0, 2)


def test_given_decorator_range_when_workspace_symbol_position_then_name_on_next_line(tmp_path):
	# given — ty often starts SymbolInformation on `@dataclass`
	src = tmp_path / "mod.py"
	src.write_text("@dataclass\nclass Foo:\n\tpass\n", encoding="utf-8")
	sym = {
		"name": "Foo",
		"kind": 5,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 0, "character": 10},
			},
		},
	}
	# when
	line = format_workspace_symbol(sym, tmp_path)
	_uri, row, col = workspace_symbol_position(sym)
	# then
	assert line == "Foo  [Class]  (mod.py:2:7)"
	assert (row, col) == (1, 6)


def test_given_stacked_decorators_when_workspace_symbol_position_then_finds_name(tmp_path):
	# given — single-line decorator range + several `@` lines before the def
	src = tmp_path / "mod.py"
	src.write_text(
		"@a\n@b\n@c\n@d\ndef target():\n\tpass\n",
		encoding="utf-8",
	)
	sym = {
		"name": "target",
		"kind": 12,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 0, "character": 2},
			},
		},
	}
	# when
	_uri, row, col = workspace_symbol_position(sym)
	# then — `def target` is line index 4; name starts after "def "
	assert (row, col) == (4, 4)


def test_given_many_symbols_when_format_workspace_symbols_then_caps_with_note(tmp_path):
	# given
	src = tmp_path / "m.py"
	src.write_text("a = 1\n", encoding="utf-8")
	symbols = [
		{
			"name": f"S{i}",
			"kind": 13,
			"location": {
				"uri": src.as_uri(),
				"range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
			},
		}
		for i in range(3)
	]
	# when
	text = format_workspace_symbols(symbols, tmp_path, limit=2)
	# then
	assert text.count("\n") == 2  # two results + truncation line
	assert "S0  [Variable]" in text
	assert "S1  [Variable]" in text
	assert "S2" not in text
	assert "… and 1 more (showing first 2)" in text


def _symbol(name: str, uri: str) -> dict:
	return {
		"name": name,
		"kind": 12,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}},
	}


def test_given_fuzzy_hits_before_exact_when_rank_then_exact_prefix_substring_order():
	# given — ty returns fuzzy subsequence hits in workspace order
	names = ["test_lsp_client_thing", "get_client", "LspClientFactory", "lspclient", "LspClient", "MyLspClient"]
	symbols = [_symbol(n, "file:///x.py") for n in names]
	# when
	ranked = [sym["name"] for sym in rank_workspace_symbols(symbols, "LspClient")]
	# then
	assert ranked == [
		"LspClient",
		"lspclient",
		"LspClientFactory",
		"MyLspClient",
		"test_lsp_client_thing",
		"get_client",
	]


def test_given_exact_match_past_cap_when_format_workspace_symbols_then_shown_first(tmp_path):
	# given
	src = tmp_path / "m.py"
	src.write_text("a = 1\n", encoding="utf-8")
	symbols = [_symbol(f"get_thing_{i}", src.as_uri()) for i in range(5)] + [_symbol("get", src.as_uri())]
	# when
	text = format_workspace_symbols(symbols, tmp_path, query="get", limit=2)
	# then
	assert text.splitlines()[0].startswith("get  [Function]")


def test_given_missing_file_when_ensure_open_then_tool_error_names_path(tmp_path):
	# given
	client = _started_client(tmp_path)
	# when
	with pytest.raises(TOOL_ERRORS) as caught:
		asyncio.run(client.ensure_open("nope/missing.py"))
	text = format_tool_error(caught.value)
	# then
	assert text.startswith("File not found: ")
	assert "missing.py" in text


def test_given_timeout_when_format_tool_error_then_mentions_retry():
	# given / when
	text = format_tool_error(TimeoutError())
	# then
	assert "timed out" in text
	assert "retry" in text


def test_given_unsupported_input_when_format_tool_error_then_passes_message_through():
	# given / when
	text = format_tool_error(ToolInputError("webnav has no language server for 'a.md'"))
	# then
	assert text == "webnav has no language server for 'a.md'"


def test_given_pending_request_when_server_exits_then_request_fails_fast(tmp_path):
	# given
	client = _started_client(tmp_path)

	async def _run() -> None:
		async def _exit() -> None:
			await asyncio.sleep(0)
			client._fail_pending()

		task = asyncio.create_task(_exit())
		# when / then — raises immediately instead of waiting out the timeout
		with pytest.raises(LanguageServerExitedError):
			await client._request("textDocument/hover", {}, timeout=5)
		await task

	asyncio.run(_run())


def test_given_never_started_when_is_alive_then_false(tmp_path):
	# given
	client = LspClient(workspace_root=tmp_path, command=["true"], language_id="python")
	# when / then
	assert client.is_alive is False
