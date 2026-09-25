"""Minimal async LSP client, written specifically for talking to `ty server`.

Not a general-purpose LSP library: framing, initialize params, and the
handful of requests used here are only verified against ty's behavior.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class NotStartedError(RuntimeError):
	pass


def resolve_ty_command(workspace_root: Path) -> list[str]:
	venv_bin = "Scripts" if sys.platform == "win32" else "bin"
	venv_exe = "ty.exe" if sys.platform == "win32" else "ty"
	candidate = workspace_root / ".venv" / venv_bin / venv_exe
	if candidate.is_file():
		return [str(candidate), "server"]
	on_path = shutil.which("ty")
	if on_path:
		return [on_path, "server"]
	return ["uv", "run", "ty", "server"]


@dataclass
class OpenFile:
	uri: str
	version: int
	mtime_ns: int
	size: int


@dataclass
class TyLspClient:
	workspace_root: Path
	command: list[str] = field(default_factory=list)
	_proc: asyncio.subprocess.Process | None = field(default=None, init=False)
	_next_id: int = field(default=0, init=False)
	_pending: dict[int, asyncio.Future] = field(default_factory=dict, init=False)
	_diagnostics: dict[str, list[dict[str, Any]]] = field(default_factory=dict, init=False)
	_open_files: dict[str, OpenFile] = field(default_factory=dict, init=False)
	_reader_task: asyncio.Task | None = field(default=None, init=False)
	_stderr_task: asyncio.Task | None = field(default=None, init=False)
	_started: bool = field(default=False, init=False)

	def __post_init__(self) -> None:
		if not self.command:
			self.command = resolve_ty_command(self.workspace_root)

	@property
	def _running_proc(self) -> asyncio.subprocess.Process:
		if self._proc is None:
			raise NotStartedError("TyLspClient.start() must be awaited before use")
		return self._proc

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
					},
					"workspace": {"workspaceFolders": True},
				},
				"workspaceFolders": [
					{"uri": self.workspace_root.as_uri(), "name": self.workspace_root.name}
				],
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
			logger.debug("ty server didn't respond to shutdown in time; terminating it directly", exc_info=True)
		if self._reader_task:
			self._reader_task.cancel()
		if self._stderr_task:
			self._stderr_task.cancel()
		with contextlib.suppress(ProcessLookupError):
			self._proc.terminate()

	# -- wire protocol -----------------------------------------------------

	async def _read_loop(self) -> None:
		proc = self._running_proc
		if proc.stdout is None:
			raise NotStartedError("ty server subprocess has no stdout pipe")
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
			raise NotStartedError("ty server subprocess has no stderr pipe")
		async for _line in proc.stderr:
			pass  # ty's own stderr logging isn't surfaced; nothing to act on here

	def _dispatch(self, msg: dict[str, Any]) -> None:
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

	def _send(self, obj: dict[str, Any]) -> None:
		proc = self._running_proc
		if proc.stdin is None:
			raise NotStartedError("ty server subprocess has no stdin pipe")
		body = json.dumps(obj).encode("utf-8")
		header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
		proc.stdin.write(header + body)

	async def _request(self, method: str, params: dict[str, Any], timeout: float = 20) -> dict[str, Any]:
		self._next_id += 1
		msg_id = self._next_id
		fut: asyncio.Future = asyncio.get_event_loop().create_future()
		self._pending[msg_id] = fut
		self._send({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params})
		stdin = self._running_proc.stdin
		if stdin is not None:
			await stdin.drain()
		try:
			return await asyncio.wait_for(fut, timeout=timeout)
		finally:
			self._pending.pop(msg_id, None)

	def _notify(self, method: str, params: dict[str, Any]) -> None:
		self._send({"jsonrpc": "2.0", "method": method, "params": params})

	# -- document sync -------------------------------------------------------

	def _to_uri(self, file_path: str) -> Path:
		p = Path(file_path)
		if not p.is_absolute():
			p = self.workspace_root / p
		return p.resolve()

	async def ensure_open(self, file_path: str) -> str:
		abs_path = self._to_uri(file_path)
		uri = abs_path.as_uri()
		stat = abs_path.stat()
		known = self._open_files.get(uri)
		if known is not None and known.mtime_ns == stat.st_mtime_ns and known.size == stat.st_size:
			return uri
		text = abs_path.read_text(encoding="utf-8")
		if known is None:
			self._notify(
				"textDocument/didOpen",
				{
					"textDocument": {
						"uri": uri,
						"languageId": "python",
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
			self._open_files[uri] = OpenFile(
				uri=uri, version=new_version, mtime_ns=stat.st_mtime_ns, size=stat.st_size
			)
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
		resp = await self._request("textDocument/diagnostic", {"textDocument": {"uri": uri}})
		result = resp.get("result") or {}
		if result.get("kind") == "unchanged":
			return self._diagnostics.get(uri, [])
		return result.get("items", [])
