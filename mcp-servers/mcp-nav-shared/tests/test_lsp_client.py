"""Fast unit tests for `mcp_nav_shared.lsp_client` (no live language servers)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from mcp_nav_shared import lsp_client
from mcp_nav_shared.lsp_client import LanguageServerExitedError, LspClient, LspRequestError


def test_given_message_when_lsp_request_error_then_exposes_method():
	# given / when
	err = LspRequestError("textDocument/hover", -32601, "Method not found")
	# then
	assert err.method == "textDocument/hover"
	assert err.code == -32601
	assert "Method not found" in str(err)


class _FakeStdin:
	def write(self, data: bytes) -> None:
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
	monkeypatch.setattr(lsp_client, "PUSH_DIAGNOSTICS_TIMEOUT", 0.01)
	# when
	items = asyncio.run(client.diagnostics(str(src)))
	# then
	assert items == cached


def test_given_empty_full_pull_and_stale_push_cache_when_diagnostics_then_trusts_pull(tmp_path, monkeypatch):
	# given
	src = tmp_path / "x.html"
	src.write_text("<p></p>\n", encoding="utf-8")
	client = _started_client(tmp_path, language_id="html")
	uri = src.resolve().as_uri()
	client._diagnostics[uri] = [{"message": "pushed", "range": {"start": {"line": 0, "character": 0}}}]

	async def _empty(_method: str, _params: dict, timeout: float = 20) -> dict:
		return {"result": {"kind": "full", "items": []}}

	monkeypatch.setattr(client, "_request", _empty)
	monkeypatch.setattr(lsp_client, "PUSH_DIAGNOSTICS_TIMEOUT", 0.01)
	# when
	items = asyncio.run(client.diagnostics(str(src)))
	# then
	assert items == []


def test_given_fixed_file_when_resynced_then_pushed_diagnostics_are_dropped(tmp_path, monkeypatch):
	# given
	src = tmp_path / "x.py"
	src.write_text("x: int = 'a'\n", encoding="utf-8")
	client = _started_client(tmp_path)
	monkeypatch.setattr(client, "_notify", lambda *_a, **_k: None)
	uri = asyncio.run(client.ensure_open(str(src)))
	client._diagnostics[uri] = [{"message": "old error"}]
	# when
	src.write_text("x: int = 1\n\n", encoding="utf-8")
	asyncio.run(client.ensure_open(str(src)))
	# then
	assert uri not in client._diagnostics


class _RecordingStdin(_FakeStdin):
	def __init__(self) -> None:
		self.written: list[bytes] = []

	def write(self, data: bytes) -> None:
		self.written.append(data)


def _sent_bodies(stdin: _RecordingStdin) -> list[dict]:
	import json

	return [json.loads(chunk.split(b"\r\n\r\n", 1)[1]) for chunk in stdin.written]


def test_given_server_requests_when_dispatched_then_client_replies(tmp_path):
	# given
	client = _started_client(tmp_path)
	stdin = _RecordingStdin()
	client._proc.stdin = stdin  # type: ignore[union-attr]
	# when
	client._dispatch({"id": 7, "method": "workspace/configuration", "params": {"items": [{}, {}]}})
	client._dispatch({"id": 8, "method": "client/registerCapability", "params": {}})
	client._dispatch({"id": 9, "method": "some/unknown", "params": {}})
	# then
	replies = {body["id"]: body for body in _sent_bodies(stdin)}
	assert replies[7]["result"] == [None, None]
	assert replies[8]["result"] is None and "error" not in replies[8]
	assert replies[9]["error"]["code"] == -32601


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


def _counting_symbol_request(client: LspClient, monkeypatch, calls: list[str]) -> None:
	async def _fake(method: str, _params: dict, timeout: float = 20) -> dict:
		calls.append(method)
		return {"result": [{"name": f"call{len(calls)}"}]}

	monkeypatch.setattr(client, "_request", _fake)
	monkeypatch.setattr(client, "_notify", lambda *_a, **_k: None)


def test_given_unchanged_file_when_document_symbol_twice_then_second_call_is_cached(tmp_path, monkeypatch):
	# given
	src = tmp_path / "a.py"
	src.write_text("x = 1\n", encoding="utf-8")
	client = _started_client(tmp_path)
	calls: list[str] = []
	_counting_symbol_request(client, monkeypatch, calls)
	# when
	first = asyncio.run(client.document_symbol(str(src)))
	second = asyncio.run(client.document_symbol(str(src)))
	# then
	assert first == second
	assert len(calls) == 1


def test_given_edited_file_when_document_symbol_then_cache_is_invalidated(tmp_path, monkeypatch):
	# given
	src = tmp_path / "a.py"
	src.write_text("x = 1\n", encoding="utf-8")
	client = _started_client(tmp_path)
	calls: list[str] = []
	_counting_symbol_request(client, monkeypatch, calls)
	first = asyncio.run(client.document_symbol(str(src)))
	# when
	src.write_text("x = 1\ny = 2\n", encoding="utf-8")
	second = asyncio.run(client.document_symbol(str(src)))
	# then
	assert len(calls) == 2
	assert first != second


def test_given_closed_scratch_document_when_reopened_then_symbols_are_not_stale(tmp_path, monkeypatch):
	# given
	client = _started_client(tmp_path)
	calls: list[str] = []
	_counting_symbol_request(client, monkeypatch, calls)
	uri = (tmp_path / "scratch.py").as_uri()
	asyncio.run(client.open_scratch_document(uri, "a = 1\n"))
	client._symbol_cache[uri] = (1, [{"name": "stale"}])
	# when
	asyncio.run(client.close_scratch_document(uri))
	# then
	assert uri not in client._symbol_cache


def test_given_ts_suffix_when_ensure_open_then_did_open_uses_mapped_language_id(tmp_path, monkeypatch):
	# given
	(tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
	(tmp_path / "b.js").write_text("export const y = 1;\n", encoding="utf-8")
	client = _started_client(tmp_path, language_id="javascript")
	client.language_ids = {".ts": "typescript"}
	sent: list[dict] = []
	monkeypatch.setattr(client, "_notify", lambda _m, params: sent.append(params["textDocument"]))
	# when
	asyncio.run(client.ensure_open(str(tmp_path / "a.ts")))
	asyncio.run(client.ensure_open(str(tmp_path / "b.js")))
	# then
	assert [d["languageId"] for d in sent] == ["typescript", "javascript"]


def test_given_push_only_server_when_diagnostics_then_waits_for_push_after_sync(tmp_path, monkeypatch):
	# given
	src = tmp_path / "a.ts"
	src.write_text("x\n", encoding="utf-8")
	client = _started_client(tmp_path, language_id="typescript")
	monkeypatch.setattr(client, "_notify", lambda *_a, **_k: None)
	uri = src.resolve().as_uri()
	pushed = [{"message": "late push"}]

	async def _reject(_method: str, _params: dict, timeout: float = 20) -> dict:
		raise LspRequestError("textDocument/diagnostic", -32601, "Unhandled method")

	monkeypatch.setattr(client, "_request", _reject)

	async def _run() -> list[dict]:
		async def _push_later() -> None:
			await asyncio.sleep(0.05)
			client._dispatch(
				{"method": "textDocument/publishDiagnostics", "params": {"uri": uri, "diagnostics": pushed}}
			)

		task = asyncio.create_task(_push_later())
		items = await client.diagnostics(str(src))
		await task
		return items

	# when
	items = asyncio.run(_run())
	# then
	assert items == pushed


def _respond_with(client: LspClient, replies: list[dict]) -> asyncio.Future:
	async def _serve() -> None:
		for reply in replies:
			while not client._pending:
				await asyncio.sleep(0)
			client._dispatch({"jsonrpc": "2.0", "id": next(iter(client._pending)), **reply})
			await asyncio.sleep(0)

	return asyncio.ensure_future(_serve())


def _run_request(client: LspClient, replies: list[dict]) -> dict:
	async def _run() -> dict:
		serving = _respond_with(client, replies)
		try:
			return await client._request("textDocument/hover", {})
		finally:
			serving.cancel()

	return asyncio.run(_run())


@pytest.fixture
def _no_backoff(monkeypatch):
	monkeypatch.setattr(lsp_client, "_CONTENT_MODIFIED_BACKOFF", (0, 0, 0))


def test_given_content_modified_once_when_request_then_retried_and_succeeds(tmp_path, _no_backoff):
	# given
	client = _started_client(tmp_path)
	replies = [{"error": {"code": -32801, "message": "content modified"}}, {"result": {"ok": 1}}]
	# when
	resp = _run_request(client, replies)
	# then
	assert resp["result"] == {"ok": 1}


def test_given_persistent_content_modified_when_request_then_error_surfaces(tmp_path, _no_backoff):
	# given
	client = _started_client(tmp_path)
	replies = [{"error": {"code": -32801, "message": "content modified"}}] * 4
	# when / then
	with pytest.raises(LspRequestError) as caught:
		_run_request(client, replies)
	assert caught.value.code == -32801


def test_given_other_error_when_request_then_not_retried(tmp_path, _no_backoff):
	# given
	client = _started_client(tmp_path)
	replies = [{"error": {"code": -32601, "message": "nope"}}, {"result": {"ok": 1}}]
	# when / then
	with pytest.raises(LspRequestError) as caught:
		_run_request(client, replies)
	assert caught.value.code == -32601
