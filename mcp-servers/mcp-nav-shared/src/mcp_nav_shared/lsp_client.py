"""Minimal async LSP client: generic JSON-RPC/LSP wire protocol plumbing.

Not a general-purpose LSP library: framing and the handful of requests used
here cover only what codenav/webnav's MCP tools need. Language-server-
specific bits (how to launch the server, its languageId, any non-default
initialize capabilities) are the caller's responsibility — pass a `command`
and `language_id` in.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Max seconds to wait for a push-only server's publishDiagnostics after a sync.
PUSH_DIAGNOSTICS_TIMEOUT = 5.0

# Server->client requests that only need an acknowledgement.
_NULL_REPLY_METHODS = {
	"client/registerCapability",
	"client/unregisterCapability",
	"window/workDoneProgress/create",
	"workspace/diagnostic/refresh",
	"workspace/semanticTokens/refresh",
	"workspace/inlayHint/refresh",
	"workspace/codeLens/refresh",
}


class NotStartedError(RuntimeError):
	pass


class LspRequestError(RuntimeError):
	"""JSON-RPC error response from the language server."""

	def __init__(self, method: str, code: Any, message: str) -> None:
		self.method = method
		self.code = code
		super().__init__(message)


class LanguageServerExitedError(RuntimeError):
	"""The language server process ended while a request was pending."""


@dataclass
class OpenFile:
	uri: str
	version: int
	mtime_ns: int
	size: int


@dataclass
class LspClient:
	workspace_root: Path
	command: list[str]
	language_id: str
	# Per-suffix override of `language_id` for servers that handle several
	# languages (e.g. typescript-language-server: `.ts` -> "typescript").
	language_ids: dict[str, str] = field(default_factory=dict)
	_proc: asyncio.subprocess.Process | None = field(default=None, init=False)
	_next_id: int = field(default=0, init=False)
	_pending: dict[int, asyncio.Future] = field(default_factory=dict, init=False)
	_diagnostics: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)
	_open_files: dict[str, OpenFile] = field(default_factory=dict, init=False)
	# uri -> event set by the first publishDiagnostics after the document was
	# last synced; lets push-only servers (typescript-language-server has no
	# pull support) be awaited instead of answered from a stale/empty cache.
	_diag_events: dict[str, asyncio.Event] = field(default_factory=dict, init=False)
	# uri -> (document version, documentSymbol result). documentSymbol depends
	# only on the one file's text, and `ensure_open` bumps the version exactly
	# when that text changes (stat mtime/size), so a version match means fresh.
	_symbol_cache: dict[str, tuple[int, list[dict[str, Any]]]] = field(default_factory=dict, init=False)
	_reader_task: asyncio.Task | None = field(default=None, init=False)
	_stderr_task: asyncio.Task | None = field(default=None, init=False)
	_started: bool = field(default=False, init=False)

	@property
	def _running_proc(self) -> asyncio.subprocess.Process:
		if self._proc is None:
			raise NotStartedError("LspClient.start() must be awaited before use")
		return self._proc

	@property
	def is_alive(self) -> bool:
		return self._proc is not None and self._proc.returncode is None

	async def start(self) -> None:
		if self._started:
			return
		self._proc = await asyncio.create_subprocess_exec(
			*self.command,
			cwd=str(self.workspace_root),
			stdin=asyncio.subprocess.PIPE,
			stdout=asyncio.subprocess.PIPE,
			stderr=asyncio.subprocess.PIPE,
		)
		self._reader_task = asyncio.create_task(self._read_loop())
		self._stderr_task = asyncio.create_task(self._drain_stderr())
		await self._request(
			"initialize",
			{
				"processId": None,
				"rootUri": self.workspace_root.as_uri(),
				"capabilities": {
					"textDocument": {
						"synchronization": {"didSave": True},
						"publishDiagnostics": {},
						"documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
						"callHierarchy": {},
						"typeHierarchy": {},
					},
					"workspace": {"workspaceFolders": True},
				},
				"workspaceFolders": [{"uri": self.workspace_root.as_uri(), "name": self.workspace_root.name}],
			},
		)
		self._notify("initialized", {})
		self._started = True

	async def stop(self) -> None:
		if self._proc is None:
			return
		try:
			await self._request("shutdown", {}, timeout=5)
			self._notify("exit", {})
		except Exception:
			logger.debug("language server didn't respond to shutdown in time; terminating it directly", exc_info=True)
		if self._reader_task:
			self._reader_task.cancel()
		if self._stderr_task:
			self._stderr_task.cancel()
		with contextlib.suppress(ProcessLookupError):
			self._proc.terminate()
		with contextlib.suppress(asyncio.TimeoutError, ProcessLookupError):
			await asyncio.wait_for(self._proc.wait(), timeout=3)
		self._started = False
		self._proc = None

	# -- wire protocol -----------------------------------------------------

	async def _read_loop(self) -> None:
		try:
			await self._read_messages()
		finally:
			self._fail_pending()

	def _fail_pending(self) -> None:
		# Without this, requests in flight when the server dies wait out their full timeout.
		pending, self._pending = self._pending, {}
		for fut in pending.values():
			if not fut.done():
				fut.set_exception(LanguageServerExitedError(f"language server exited: {' '.join(self.command)}"))

	async def _read_messages(self) -> None:
		proc = self._running_proc
		if proc.stdout is None:
			raise NotStartedError("language server subprocess has no stdout pipe")
		stream = proc.stdout
		while True:
			header = b""
			while not header.endswith(b"\r\n\r\n"):
				chunk = await stream.read(1)
				if not chunk:
					return
				header += chunk
			length = 0
			for line in header.split(b"\r\n"):
				if line.lower().startswith(b"content-length"):
					length = int(line.split(b":")[1].strip())
			body = await stream.readexactly(length)
			try:
				msg = json.loads(body)
			except json.JSONDecodeError:
				continue
			self._dispatch(msg)

	async def _drain_stderr(self) -> None:
		proc = self._running_proc
		if proc.stderr is None:
			raise NotStartedError("language server subprocess has no stderr pipe")
		async for _line in proc.stderr:
			pass  # the language server's own stderr logging isn't surfaced; nothing to act on here

	def _reply_to_server_request(self, msg: dict[str, Any]) -> None:
		"""Answer a server->client request so the server never waits on us
		(`workspace/configuration`, `client/registerCapability`, progress
		creation, ...). Unknown methods get MethodNotFound."""
		method = msg.get("method")
		if method == "workspace/configuration":
			items = (msg.get("params") or {}).get("items") or []
			reply: dict[str, Any] = {"result": [None] * len(items)}
		elif method in _NULL_REPLY_METHODS:
			reply = {"result": None}
		else:
			reply = {"error": {"code": -32601, "message": f"Method not found: {method}"}}
		try:
			self._send({"jsonrpc": "2.0", "id": msg["id"], **reply})
		except (NotStartedError, OSError, RuntimeError):
			logger.debug("could not reply to server request %s", method, exc_info=True)

	def _dispatch(self, msg: dict[str, Any]) -> None:
		if "id" in msg and "method" in msg:
			self._reply_to_server_request(msg)
			return
		if "id" in msg and "method" not in msg:
			fut = self._pending.pop(msg["id"], None)
			if fut is not None and not fut.done():
				fut.set_result(msg)
			return
		method = msg.get("method")
		if method == "textDocument/publishDiagnostics":
			params = msg.get("params", {})
			uri = params.get("uri")
			if uri:
				self._diagnostics[uri] = params.get("diagnostics", [])
				event = self._diag_events.get(uri)
				if event is not None:
					event.set()

	def _send(self, obj: dict[str, Any]) -> None:
		proc = self._running_proc
		if proc.stdin is None:
			raise NotStartedError("language server subprocess has no stdin pipe")
		body = json.dumps(obj).encode("utf-8")
		header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
		proc.stdin.write(header + body)

	async def _request(self, method: str, params: dict[str, Any], timeout: float = 20) -> dict[str, Any]:
		self._next_id += 1
		msg_id = self._next_id
		fut: asyncio.Future = asyncio.get_running_loop().create_future()
		self._pending[msg_id] = fut
		self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
		stdin = self._running_proc.stdin
		if stdin is not None:
			await stdin.drain()
		try:
			resp = await asyncio.wait_for(fut, timeout=timeout)
		finally:
			self._pending.pop(msg_id, None)
		if "error" in resp:
			err = resp["error"] or {}
			raise LspRequestError(method, err.get("code"), str(err.get("message", err)))
		return resp

	def _notify(self, method: str, params: dict[str, Any]) -> None:
		self._send({"jsonrpc": "2.0", "method": method, "params": params})

	# -- document sync -------------------------------------------------------

	def _to_uri(self, file_path: str) -> Path:
		p = Path(file_path)
		if not p.is_absolute():
			p = self.workspace_root / p
		return p.resolve()

	def _language_id_for(self, path: Path) -> str:
		return self.language_ids.get(path.suffix.lower(), self.language_id)

	async def ensure_open(self, file_path: str) -> str:
		abs_path = self._to_uri(file_path)
		uri = abs_path.as_uri()
		stat = abs_path.stat()
		known = self._open_files.get(uri)
		if known is not None and known.mtime_ns == stat.st_mtime_ns and known.size == stat.st_size:
			return uri
		text = abs_path.read_text(encoding="utf-8")
		self._diag_events[uri] = asyncio.Event()
		# The previous version's pushed diagnostics describe text that no longer
		# exists; keeping them would resurface fixed errors as a "cache fallback".
		if known is not None:
			self._diagnostics.pop(uri, None)
		if known is None:
			self._notify(
				"textDocument/didOpen",
				{
					"textDocument": {
						"uri": uri,
						"languageId": self._language_id_for(abs_path),
						"version": 1,
						"text": text,
					}
				},
			)
			self._open_files[uri] = OpenFile(uri=uri, version=1, mtime_ns=stat.st_mtime_ns, size=stat.st_size)
		else:
			new_version = known.version + 1
			self._notify(
				"textDocument/didChange",
				{
					"textDocument": {"uri": uri, "version": new_version},
					"contentChanges": [{"text": text}],
				},
			)
			self._open_files[uri] = OpenFile(uri=uri, version=new_version, mtime_ns=stat.st_mtime_ns, size=stat.st_size)
		return uri

	# -- LSP calls used by the MCP tools --------------------------------------

	async def hover(self, file_path: str, line: int, column: int) -> dict[str, Any]:
		uri = await self.ensure_open(file_path)
		resp = await self._request(
			"textDocument/hover",
			{"textDocument": {"uri": uri}, "position": {"line": line - 1, "character": column - 1}},
		)
		return resp.get("result") or {}

	async def definition(self, file_path: str, line: int, column: int) -> list[dict[str, Any]]:
		uri = await self.ensure_open(file_path)
		resp = await self._request(
			"textDocument/definition",
			{"textDocument": {"uri": uri}, "position": {"line": line - 1, "character": column - 1}},
		)
		result = resp.get("result")
		if result is None:
			return []
		return result if isinstance(result, list) else [result]

	async def references(
		self, file_path: str, line: int, column: int, *, include_declaration: bool = True
	) -> list[dict[str, Any]]:
		uri = await self.ensure_open(file_path)
		resp = await self._request(
			"textDocument/references",
			{
				"textDocument": {"uri": uri},
				"position": {"line": line - 1, "character": column - 1},
				"context": {"includeDeclaration": include_declaration},
			},
		)
		return resp.get("result") or []

	async def workspace_symbol(self, query: str) -> list[dict[str, Any]]:
		resp = await self._request("workspace/symbol", {"query": query})
		return resp.get("result") or []

	async def diagnostics(self, file_path: str) -> list[dict[str, Any]]:
		uri = await self.ensure_open(file_path)
		cached = self._diagnostics.get(uri, [])
		try:
			resp = await self._request("textDocument/diagnostic", {"textDocument": {"uri": uri}})
		except LspRequestError:
			# HTML/CSS/TS servers often only push publishDiagnostics and reject
			# pull. If the document was just (re)synced, the push for this
			# version hasn't necessarily arrived yet: wait for it rather than
			# report the previous version's (or an empty) result.
			event = self._diag_events.get(uri)
			if event is not None and not event.is_set():
				with contextlib.suppress(TimeoutError):
					await asyncio.wait_for(event.wait(), timeout=PUSH_DIAGNOSTICS_TIMEOUT)
			return self._diagnostics.get(uri, [])
		result = resp.get("result") or {}
		if result.get("kind") == "unchanged":
			return cached
		items = result.get("items")
		if items is None:
			return cached
		# A pull answer for the current version is authoritative, empty included.
		return items

	async def document_symbol(self, file_path: str) -> list[dict[str, Any]]:
		uri = await self.ensure_open(file_path)
		version = self._open_files[uri].version
		hit = self._symbol_cache.get(uri)
		if hit is not None and hit[0] == version:
			return hit[1]
		resp = await self._request("textDocument/documentSymbol", {"textDocument": {"uri": uri}})
		result = resp.get("result") or []
		self._symbol_cache[uri] = (version, result)
		return result

	async def prepare_call_hierarchy(self, file_path: str, line: int, column: int) -> list[dict[str, Any]]:
		uri = await self.ensure_open(file_path)
		resp = await self._request(
			"textDocument/prepareCallHierarchy",
			{"textDocument": {"uri": uri}, "position": {"line": line - 1, "character": column - 1}},
		)
		return resp.get("result") or []

	async def incoming_calls(self, item: dict[str, Any]) -> list[dict[str, Any]]:
		resp = await self._request("callHierarchy/incomingCalls", {"item": item})
		return resp.get("result") or []

	async def prepare_type_hierarchy(self, file_path: str, line: int, column: int) -> list[dict[str, Any]]:
		uri = await self.ensure_open(file_path)
		resp = await self._request(
			"textDocument/prepareTypeHierarchy",
			{"textDocument": {"uri": uri}, "position": {"line": line - 1, "character": column - 1}},
		)
		return resp.get("result") or []

	async def supertypes(self, item: dict[str, Any]) -> list[dict[str, Any]]:
		resp = await self._request("typeHierarchy/supertypes", {"item": item})
		return resp.get("result") or []

	# -- scratch (in-memory-only) documents -----------------------------------
	#
	# For codenav's Protocol-conformance probe: a document that is never
	# written to disk, so it can't use `ensure_open`'s stat/read-based sync.

	async def open_scratch_document(self, uri: str, text: str) -> None:
		self._notify(
			"textDocument/didOpen",
			{"textDocument": {"uri": uri, "languageId": self.language_id, "version": 1, "text": text}},
		)
		self._open_files[uri] = OpenFile(uri=uri, version=1, mtime_ns=-1, size=len(text))

	async def change_scratch_document(self, uri: str, text: str) -> None:
		version = self._open_files[uri].version + 1
		self._notify(
			"textDocument/didChange",
			{"textDocument": {"uri": uri, "version": version}, "contentChanges": [{"text": text}]},
		)
		self._open_files[uri] = OpenFile(uri=uri, version=version, mtime_ns=-1, size=len(text))

	async def close_scratch_document(self, uri: str) -> None:
		self._notify("textDocument/didClose", {"textDocument": {"uri": uri}})
		self._open_files.pop(uri, None)
		self._diagnostics.pop(uri, None)
		# Reopening restarts versions at 1, which could falsely match an old entry.
		self._symbol_cache.pop(uri, None)

	async def pull_diagnostics(self, uri: str) -> list[dict[str, Any]]:
		"""Pull diagnostics for an already-open `uri` directly, with no cache
		fallback — used for the scratch-document probe above, where there is no
		prior `publishDiagnostics` push to fall back to."""
		resp = await self._request("textDocument/diagnostic", {"textDocument": {"uri": uri}})
		result = resp.get("result") or {}
		return result.get("items") or []
