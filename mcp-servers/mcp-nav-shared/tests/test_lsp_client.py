"""Fast unit tests for `mcp_nav_shared.lsp_client` (no live language servers)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp_nav_shared.lsp_client import LanguageServerExitedError, LspClient, LspRequestError


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
