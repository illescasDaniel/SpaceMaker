"""Fast unit tests for codenav/webnav shared MCP helpers (no live language servers)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest


_MCP_ROOT = Path(__file__).resolve().parents[2] / "mcp-servers"
if str(_MCP_ROOT) not in sys.path:
	sys.path.insert(0, str(_MCP_ROOT))

from _shared.format import format_location, uri_to_relative  # noqa: E402
from _shared.lsp_client import LspClient, LspRequestError  # noqa: E402
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
