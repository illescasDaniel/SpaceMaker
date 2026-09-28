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
	format_callers,
	format_diagnostic,
	format_diagnostics,
	format_location,
	format_outline,
	format_references,
	format_references_grouped,
	format_workspace_symbol,
	format_workspace_symbols,
	is_hierarchical_document_symbols,
	rank_workspace_symbols,
	to_symbol_tree,
	uri_to_relative,
	workspace_symbol_position,
)
from _shared.lsp_client import LanguageServerExitedError, LspClient, LspRequestError  # noqa: E402
from _shared.resolve import SymbolResolutionError, resolve_symbol  # noqa: E402
from _shared.workspace import resolve_source_root, resolve_workspace_root  # noqa: E402
from codenav_mcp import server as codenav_server  # noqa: E402
from codenav_mcp.server import _check_python_file, _protocol_class_names  # noqa: E402


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


def _diagnostic(line: int, message: str, severity: int = 1) -> dict:
	return {
		"range": {"start": {"line": line, "character": 0}, "end": {"line": line, "character": 1}},
		"severity": severity,
		"message": message,
	}


def test_given_no_items_when_format_diagnostics_then_no_diagnostics_message():
	# given / when
	text = format_diagnostics([])
	# then
	assert text == "No diagnostics."


def test_given_few_items_when_format_diagnostics_then_one_line_per_item_no_truncation():
	# given
	items = [_diagnostic(0, "bad thing", severity=1), _diagnostic(4, "a hint", severity=4)]
	# when
	text = format_diagnostics(items)
	# then
	lines = text.splitlines()
	assert lines == ["1:1 [error] bad thing", "5:1 [hint] a hint"]


def test_given_many_items_when_format_diagnostics_then_caps_with_note():
	# given — mirrors test_given_many_symbols_when_format_workspace_symbols_then_caps_with_note
	items = [_diagnostic(i, f"error {i}") for i in range(5)]
	# when
	text = format_diagnostics(items, limit=2)
	# then
	lines = text.splitlines()
	assert lines == ["1:1 [error] error 0", "2:1 [error] error 1", "… and 3 more (showing first 2)"]


def test_given_multiline_message_when_format_diagnostic_then_continuation_indented():
	# given — ty's "Code is unreachable" carries a second, unprefixed line;
	# without indenting it, it reads as its own diagnostic
	item = _diagnostic(719, "Code is unreachable\nThis may depend on your current environment and settings")
	# when
	text = format_diagnostic(item)
	# then
	assert text.splitlines() == [
		"720:1 [error] Code is unreachable",
		"    This may depend on your current environment and settings",
	]


def test_given_code_when_format_diagnostic_then_appended_to_severity_tag():
	# given
	item = _diagnostic(0, "bad call", severity=2)
	item["code"] = "invalid-argument-type"
	# when
	text = format_diagnostic(item)
	# then
	assert text == "1:1 [warning invalid-argument-type] bad call"


def test_given_no_code_when_format_diagnostic_then_tag_is_severity_only():
	# given — the plain messages already covered above must not grow a
	# trailing space or "None" once `code` is read
	item = _diagnostic(0, "bad thing", severity=1)
	# when
	text = format_diagnostic(item)
	# then
	assert text == "1:1 [error] bad thing"


def test_given_multiline_message_when_format_diagnostics_then_still_one_entry_in_cap_count():
	# given — a multi-line message must count as one item against the cap,
	# not one per physical line
	items = [
		_diagnostic(0, "first\nsecond line"),
		_diagnostic(1, "another"),
	]
	# when
	text = format_diagnostics(items, limit=5)
	# then
	assert text.splitlines() == [
		"1:1 [error] first",
		"    second line",
		"2:1 [error] another",
	]


def test_given_python_file_when_check_python_file_then_no_error():
	# given / when / then — .py and .pyi are both accepted, no exception raised
	_check_python_file("src/spacemaker/bootstrap/services.py")
	_check_python_file("src/spacemaker/stubs/foo.pyi")


def test_given_non_python_file_when_check_python_file_then_tool_input_error():
	# given — a non-Python file must be rejected before it ever reaches ty,
	# which would otherwise mis-parse it as Python (e.g. diagnostics on a
	# README producing a wall of bogus syntax errors)
	# when
	with pytest.raises(ToolInputError) as caught:
		_check_python_file("README.md")
	# then
	text = format_tool_error(caught.value)
	assert text == "codenav only supports Python files (.py/.pyi), got 'README.md'"


# -- Phase B: to_symbol_tree / outline / callers / references_grouped / resolve_symbol ----


def _flat_class_and_method() -> list[dict]:
	# given — ty's flat SymbolInformation for a class containing one method
	return [
		{
			"name": "Foo",
			"kind": 5,
			"location": {"range": {"start": {"line": 0, "character": 0}, "end": {"line": 3, "character": 0}}},
		},
		{
			"name": "bar",
			"kind": 6,
			"location": {"range": {"start": {"line": 1, "character": 1}, "end": {"line": 2, "character": 0}}},
		},
	]


def _hierarchical_class_and_method() -> list[dict]:
	# given — the same shape, but as nested DocumentSymbol (hierarchicalDocumentSymbolSupport)
	return [
		{
			"name": "Foo",
			"kind": 5,
			"range": {"start": {"line": 0, "character": 0}, "end": {"line": 3, "character": 0}},
			"children": [
				{
					"name": "bar",
					"kind": 6,
					"range": {"start": {"line": 1, "character": 1}, "end": {"line": 2, "character": 0}},
					"children": [],
				}
			],
		}
	]


def test_given_location_field_when_is_hierarchical_document_symbols_then_false():
	assert is_hierarchical_document_symbols(_flat_class_and_method()) is False


def test_given_range_field_when_is_hierarchical_document_symbols_then_true():
	assert is_hierarchical_document_symbols(_hierarchical_class_and_method()) is True


def test_given_empty_list_when_is_hierarchical_document_symbols_then_false():
	assert is_hierarchical_document_symbols([]) is False


def test_given_flat_symbol_information_when_to_symbol_tree_then_nests_by_containment():
	# when
	tree = to_symbol_tree(_flat_class_and_method())
	# then
	assert len(tree) == 1
	assert tree[0]["name"] == "Foo"
	assert [c["name"] for c in tree[0]["children"]] == ["bar"]


def test_given_hierarchical_document_symbols_when_to_symbol_tree_then_keeps_nesting():
	# when
	tree = to_symbol_tree(_hierarchical_class_and_method())
	# then
	assert tree[0]["name"] == "Foo"
	assert tree[0]["children"][0]["name"] == "bar"


def test_given_no_symbols_when_format_outline_then_message():
	assert format_outline([]) == "No symbols found."


def test_given_hierarchical_symbols_when_format_outline_then_indents_children():
	# when
	text = format_outline(_hierarchical_class_and_method())
	# then
	assert text.splitlines() == [
		"Foo  [Class]  :1",
		"  bar  [Method]  :2",
	]


def test_given_flat_symbols_when_format_outline_then_nests_and_indents():
	# when
	text = format_outline(_flat_class_and_method())
	# then
	assert text.splitlines() == [
		"Foo  [Class]  :1",
		"  bar  [Method]  :2",
	]


def test_given_no_calls_when_format_callers_then_message(tmp_path):
	assert format_callers([], tmp_path) == "No callers found."


def test_given_incoming_calls_when_format_callers_then_lists_call_sites(tmp_path):
	# given
	call = {
		"from": {
			"name": "caller_fn",
			"kind": 12,
			"uri": (tmp_path / "a.py").as_uri(),
			"selectionRange": {"start": {"line": 4, "character": 0}},
		},
		"fromRanges": [
			{"start": {"line": 9, "character": 0}},
			{"start": {"line": 12, "character": 0}},
		],
	}
	# when
	text = format_callers([call], tmp_path)
	# then
	assert text == "caller_fn  [Function]  (a.py:5) calls at L10, L13"


def test_given_no_locations_when_format_references_grouped_then_message(tmp_path):
	assert format_references_grouped([], tmp_path) == "No references found."


def test_given_locations_when_format_references_grouped_then_groups_by_file_with_count(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 0, "character": 0}}},
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 5, "character": 0}}},
		{"uri": (tmp_path / "b.py").as_uri(), "range": {"start": {"line": 2, "character": 0}}},
	]
	# when
	text = format_references_grouped(locs, tmp_path)
	# then
	assert text.splitlines() == [
		"3 reference(s) in 2 file(s):",
		"a.py: L1, L6",
		"b.py: L3",
	]


def test_given_more_files_than_limit_when_format_references_grouped_then_notes_omitted(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / f"f{i}.py").as_uri(), "range": {"start": {"line": 0, "character": 0}}} for i in range(3)
	]
	# when
	text = format_references_grouped(locs, tmp_path, file_limit=2)
	lines = text.splitlines()
	# then
	assert lines[0] == "3 reference(s) in 3 file(s):"
	assert lines[-1] == "… and 1 more file(s)"


def test_given_locations_at_or_under_limit_when_format_references_then_full_snippets(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 0, "character": 0}}},
		{"uri": (tmp_path / "b.py").as_uri(), "range": {"start": {"line": 2, "character": 0}}},
	]
	# when
	text = format_references(locs, tmp_path, snippet_limit=2)
	# then
	assert text == "\n\n".join(format_location(loc, tmp_path) for loc in locs)


def test_given_locations_over_limit_when_format_references_then_compact_grouped_with_columns(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 0, "character": 4}}},
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 5, "character": 0}}},
		{"uri": (tmp_path / "b.py").as_uri(), "range": {"start": {"line": 2, "character": 0}}},
	]
	# when
	text = format_references(locs, tmp_path, snippet_limit=2)
	# then
	assert text.splitlines() == [
		"(compact list: 3 > 2 hits)",
		"3 reference(s) in 2 file(s):",
		"a.py: L1:5, L6:1",
		"b.py: L3:1",
	]


def test_given_no_locations_when_format_references_then_message(tmp_path):
	assert format_references([], tmp_path) == "No references found at that position."


class _FakeResolveClient:
	"""Duck-typed stand-in for LspClient: resolve_symbol only calls
	`workspace_symbol`/`document_symbol`, both trivial to fake for these tests."""

	def __init__(self, workspace_symbols: list[dict], document_symbols: list[dict] | None = None) -> None:
		self._workspace_symbols = workspace_symbols
		self._document_symbols = document_symbols or []

	async def workspace_symbol(self, query: str) -> list[dict]:
		return self._workspace_symbols

	async def document_symbol(self, file_path: str) -> list[dict]:
		return self._document_symbols


def test_given_single_exact_match_when_resolve_symbol_then_resolves_position(tmp_path):
	# given
	uri = (tmp_path / "pkg" / "mod.py").as_uri()
	sym = {
		"name": "target_fn",
		"kind": 12,
		"location": {"uri": uri, "range": {"start": {"line": 3, "character": 0}, "end": {"line": 3, "character": 9}}},
		"selectionRange": {"start": {"line": 3, "character": 4}, "end": {"line": 3, "character": 13}},
	}
	client = _FakeResolveClient([sym])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "target_fn"))
	# then
	assert resolved.name == "target_fn"
	assert resolved.uri == uri
	assert (resolved.line, resolved.column) == (3, 4)


def test_given_no_match_when_resolve_symbol_then_raises(tmp_path):
	# given
	client = _FakeResolveClient([])
	# when / then
	with pytest.raises(SymbolResolutionError, match="No symbol found"):
		asyncio.run(resolve_symbol(client, tmp_path, "missing"))


def test_given_two_exact_matches_when_resolve_symbol_then_ambiguous_lists_candidates(tmp_path):
	# given
	uri_a = (tmp_path / "a.py").as_uri()
	uri_b = (tmp_path / "b.py").as_uri()
	sym_a = {
		"name": "run",
		"kind": 12,
		"location": {"uri": uri_a, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}},
	}
	sym_b = {
		"name": "run",
		"kind": 12,
		"location": {"uri": uri_b, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}},
	}
	client = _FakeResolveClient([sym_a, sym_b])
	# when / then
	with pytest.raises(SymbolResolutionError) as caught:
		asyncio.run(resolve_symbol(client, tmp_path, "run"))
	text = str(caught.value)
	assert "2 symbols match 'run'" in text
	assert "a.py" in text
	assert "b.py" in text


def test_given_file_path_when_two_exact_matches_then_narrows_to_match(tmp_path):
	# given
	uri_a = (tmp_path / "a.py").as_uri()
	uri_b = (tmp_path / "b.py").as_uri()
	range_ = {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}
	sym_a = {"name": "run", "kind": 12, "location": {"uri": uri_a, "range": range_}, "selectionRange": range_}
	sym_b = {"name": "run", "kind": 12, "location": {"uri": uri_b, "range": range_}, "selectionRange": range_}
	client = _FakeResolveClient([sym_a, sym_b])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "run", file_path="b.py"))
	# then
	assert resolved.uri == uri_b


def test_given_case_exact_and_case_insensitive_match_when_resolve_symbol_then_prefers_exact_case(tmp_path):
	# given: `repo_root` (a function) and `REPO_ROOT` (a constant elsewhere)
	# both match case-insensitively; asking for the lowercase name should
	# resolve straight to the case-exact one instead of raising ambiguous.
	uri_exact = (tmp_path / "a.py").as_uri()
	uri_other = (tmp_path / "b.py").as_uri()
	range_ = {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 9}}
	exact = {"name": "repo_root", "kind": 12, "location": {"uri": uri_exact, "range": range_}, "selectionRange": range_}
	other_case = {
		"name": "REPO_ROOT",
		"kind": 13,
		"location": {"uri": uri_other, "range": range_},
		"selectionRange": range_,
	}
	client = _FakeResolveClient([exact, other_case])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "repo_root"))
	# then
	assert resolved.name == "repo_root"
	assert resolved.uri == uri_exact


def test_given_dotted_query_when_hierarchical_members_then_finds_child_node(tmp_path):
	# given
	uri = (tmp_path / "svc.py").as_uri()
	container_sym = {
		"name": "AppServices",
		"kind": 5,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}}},
		"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
	}
	members = [
		{
			"name": "AppServices",
			"kind": 5,
			"range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}},
			"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
			"children": [
				{
					"name": "enter_module",
					"kind": 6,
					"range": {"start": {"line": 5, "character": 1}, "end": {"line": 7, "character": 0}},
					"selectionRange": {"start": {"line": 5, "character": 5}, "end": {"line": 5, "character": 17}},
					"children": [],
				}
			],
		}
	]
	client = _FakeResolveClient([container_sym], members)
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "AppServices.enter_module"))
	# then
	assert resolved.name == "enter_module"
	assert (resolved.line, resolved.column) == (5, 5)


def test_given_dotted_query_when_flat_members_then_matches_within_container_range(tmp_path):
	# given — no hierarchicalDocumentSymbolSupport: fall back to range containment
	uri = (tmp_path / "svc.py").as_uri()
	container_sym = {
		"name": "AppServices",
		"kind": 5,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}}},
		"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
	}
	member_sym = {
		"name": "enter_module",
		"kind": 6,
		"location": {"uri": uri, "range": {"start": {"line": 5, "character": 1}, "end": {"line": 7, "character": 0}}},
		"selectionRange": {"start": {"line": 5, "character": 5}, "end": {"line": 5, "character": 17}},
	}
	client = _FakeResolveClient([container_sym], [container_sym, member_sym])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "AppServices.enter_module"))
	# then
	assert resolved.name == "enter_module"
	assert (resolved.line, resolved.column) == (5, 5)


def test_given_dotted_query_when_member_missing_then_raises(tmp_path):
	# given
	uri = (tmp_path / "svc.py").as_uri()
	container_sym = {
		"name": "AppServices",
		"kind": 5,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}}},
		"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
	}
	client = _FakeResolveClient([container_sym], [])
	# when / then
	with pytest.raises(SymbolResolutionError):
		asyncio.run(resolve_symbol(client, tmp_path, "AppServices.missing_method"))


def test_given_plain_protocol_base_when_protocol_class_names_then_included():
	source = "from typing import Protocol\n\nclass Port(Protocol):\n\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == {"Port"}


def test_given_qualified_protocol_base_when_protocol_class_names_then_included():
	source = "import typing\n\nclass Port(typing.Protocol):\n\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == {"Port"}


def test_given_subscripted_protocol_base_when_protocol_class_names_then_included():
	source = "from typing import Protocol\nfrom typing import TypeVar\n\nT = TypeVar('T')\n\nclass Port(Protocol[T]):\n\tpass\n"
	assert _protocol_class_names(source) == {"Port"}


def test_given_non_protocol_class_when_protocol_class_names_then_excluded():
	source = "class AppServices:\n\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == set()


def test_given_nested_protocol_class_when_protocol_class_names_then_found_at_any_depth():
	source = "from typing import Protocol\n\nclass Outer:\n\tclass Inner(Protocol):\n\t\tdef run(self) -> None: ...\n"
	assert _protocol_class_names(source) == {"Inner"}


def test_given_no_source_root_env_when_module_loaded_then_source_root_defaults_to_workspace_root():
	# codenav_mcp.server reads CODENAV_MCP_SOURCE_ROOT once at import time; in
	# a plain test environment (no .mcp.json-injected env) it should fall back
	# to scanning/deriving import paths against the whole workspace, not a
	# hardcoded "src" layout.
	assert codenav_server.SOURCE_ROOT == codenav_server.WORKSPACE_ROOT


def test_given_explicit_source_root_env_when_resolve_source_root_then_used(tmp_path, monkeypatch):
	# given
	monkeypatch.setenv("SOME_SOURCE_ROOT", "src")
	# when
	root = resolve_source_root("SOME_SOURCE_ROOT", tmp_path)
	# then
	assert root == (tmp_path / "src").resolve()


def test_given_no_source_root_env_when_resolve_source_root_then_defaults_to_workspace_root(tmp_path, monkeypatch):
	# given
	monkeypatch.delenv("SOME_OTHER_SOURCE_ROOT", raising=False)
	# when
	root = resolve_source_root("SOME_OTHER_SOURCE_ROOT", tmp_path)
	# then
	assert root == tmp_path
