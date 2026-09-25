"""codenav: MCP server exposing ty's language-server features (hover,
definition, references, workspace symbol search, diagnostics) as MCP tools.

Named "codenav" (not "ty") since ty is Astral's name for the underlying
type checker/language server this wraps — the MCP server itself is a
thin, project-specific tool built on top of it.

Built specifically for ty rather than as a generic LSP bridge: see
docs/agent-tooling.md for why (mcp-language-server's name-based
definition/references tools don't resolve symbols against ty, even though
ty's own workspace/symbol implementation answers those same queries
correctly when asked directly over LSP).

Run standalone for manual testing:
    uv run python mcp-servers/codenav_mcp/server.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


sys.path.insert(0, str(Path(__file__).resolve().parent))

from lsp_client import TyLspClient  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402


WORKSPACE_ROOT = Path(os.environ.get("CODENAV_MCP_WORKSPACE", Path.cwd())).resolve()

mcp = MCPServer(
	name="codenav",
	instructions=(
		"Code navigation for this Python codebase, backed by ty (Astral's type "
		"checker/language server). Prefer this over grepping for symbol "
		"definitions/usages: it resolves through type inference (imports, "
		"dependency-injected parameters, dataclass fields, etc.), not just text "
		"matching."
	),
)

_client: TyLspClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> TyLspClient:
	global _client
	async with _client_lock:
		if _client is None:
			_client = TyLspClient(workspace_root=WORKSPACE_ROOT)
			await _client.start()
		return _client


def _uri_to_relative(uri: str) -> str:
	parsed = urlparse(uri)
	path = Path(unquote(parsed.path.lstrip("/") if os.name == "nt" else parsed.path))
	try:
		return str(path.relative_to(WORKSPACE_ROOT)).replace("\\", "/")
	except ValueError:
		return str(path)


def _snippet(uri: str, start_line: int, end_line: int, *, context: int = 0) -> str:
	parsed = urlparse(uri)
	path = Path(unquote(parsed.path.lstrip("/") if os.name == "nt" else parsed.path))
	try:
		lines = path.read_text(encoding="utf-8").splitlines()
	except OSError:
		return ""
	lo = max(0, start_line - context)
	hi = min(len(lines), end_line + 1 + context)
	numbered = [f"{i + 1:>5} | {lines[i]}" for i in range(lo, hi)]
	return "\n".join(numbered)


def _format_location(loc: dict) -> str:
	uri = loc.get("uri") or loc.get("targetUri", "")
	rng = loc.get("range") or loc.get("targetRange", {})
	start = rng.get("start", {})
	end = rng.get("end", {})
	start_line = start.get("line", 0)
	end_line = end.get("line", start_line)
	rel = _uri_to_relative(uri)
	header = f"{rel}:{start_line + 1}"
	snippet = _snippet(uri, start_line, end_line, context=2)
	return f"{header}\n{snippet}" if snippet else header


@mcp.tool()
async def hover(file_path: str, line: int, column: int) -> str:
	"""Get type/documentation info for the symbol at a position (1-indexed line/column)."""
	client = await get_client()
	result = await client.hover(file_path, line, column)
	contents = result.get("contents")
	if not contents:
		return "No hover information at that position."
	if isinstance(contents, dict):
		return contents.get("value", str(contents))
	if isinstance(contents, list):
		return "\n".join(c.get("value", str(c)) if isinstance(c, dict) else str(c) for c in contents)
	return str(contents)


@mcp.tool()
async def definition(file_path: str, line: int, column: int) -> str:
	"""Go to the definition of the symbol at a position (1-indexed line/column).

	Resolves through ty's type inference, so this works even when the call
	site only has a typed parameter/attribute (e.g. `services.some_method()`
	where `services: AppServices` is a constructor argument), not just
	direct references to a name in scope.
	"""
	client = await get_client()
	locations = await client.definition(file_path, line, column)
	if not locations:
		return "No definition found at that position."
	return "\n\n".join(_format_location(loc) for loc in locations)


@mcp.tool()
async def references(file_path: str, line: int, column: int, include_declaration: bool = True) -> str:
	"""Find all usages of the symbol at a position (1-indexed line/column) across the workspace."""
	client = await get_client()
	locations = await client.references(file_path, line, column, include_declaration=include_declaration)
	if not locations:
		return "No references found at that position."
	return "\n\n".join(_format_location(loc) for loc in locations)


@mcp.tool()
async def search_symbol(query: str) -> str:
	"""Search the whole workspace for a symbol by name (class, function, method, etc.).

	Use this to find a symbol's file/position first, then pass that position
	to definition/references/hover for precise, type-resolved navigation.
	"""
	client = await get_client()
	symbols = await client.workspace_symbol(query)
	if not symbols:
		return f"No symbols matching {query!r}."
	lines = []
	for sym in symbols:
		loc = sym.get("location", {})
		rng = loc.get("range", {})
		start = rng.get("start", {})
		rel = _uri_to_relative(loc.get("uri", ""))
		lines.append(f"{sym.get('name', '?')}  ({rel}:{start.get('line', 0) + 1}:{start.get('character', 0) + 1})")
	return "\n".join(lines)


@mcp.tool()
async def diagnostics(file_path: str) -> str:
	"""Get ty's type-check diagnostics (errors/warnings) for a single file."""
	client = await get_client()
	items = await client.diagnostics(file_path)
	if not items:
		return "No diagnostics."
	lines = []
	for item in items:
		rng = item.get("range", {})
		start = rng.get("start", {})
		severity = {1: "error", 2: "warning", 3: "info", 4: "hint"}.get(item.get("severity"), "?")
		lines.append(
			f"{start.get('line', 0) + 1}:{start.get('character', 0) + 1} [{severity}] {item.get('message', '')}"
		)
	return "\n".join(lines)


if __name__ == "__main__":
	mcp.run(transport="stdio")
