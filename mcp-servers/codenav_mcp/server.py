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
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _shared.format import format_location, uri_to_relative  # noqa: E402
from _shared.lsp_client import LspClient, LspRequestError  # noqa: E402
from _shared.workspace import resolve_workspace_root  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402
from ty_command import resolve_ty_command  # noqa: E402


WORKSPACE_ROOT = resolve_workspace_root("CODENAV_MCP_WORKSPACE")

_POSITION_NOTE = (
	"Positions are 1-indexed. `column` is a UTF-16 character offset on the "
	"line (not a visual/display column): a leading tab counts as one "
	"character, so after a single tab the next character starts at column 2."
)

mcp = MCPServer(
	name="codenav",
	instructions=(
		"Code navigation for this Python codebase, backed by ty (Astral's type "
		"checker/language server). Prefer this over grepping for symbol "
		"definitions/usages: it resolves through type inference (imports, "
		"dependency-injected parameters, dataclass fields, etc.), not just text "
		"matching. " + _POSITION_NOTE
	),
)

_client: LspClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> LspClient:
	global _client
	async with _client_lock:
		if _client is None:
			_client = LspClient(
				workspace_root=WORKSPACE_ROOT,
				command=resolve_ty_command(WORKSPACE_ROOT),
				language_id="python",
			)
			await _client.start()
		return _client


def _format_lsp_error(exc: LspRequestError) -> str:
	return f"LSP error on {exc.method}: {exc}"


@mcp.tool()
async def hover(file_path: str, line: int, column: int) -> str:
	"""Get type/documentation info for the symbol at a position.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character.
	"""
	try:
		client = await get_client()
		result = await client.hover(file_path, line, column)
	except LspRequestError as exc:
		return _format_lsp_error(exc)
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
	"""Go to the definition of the symbol at a position.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character.

	Resolves through ty's type inference, so this works even when the call
	site only has a typed parameter/attribute (e.g. `services.some_method()`
	where `services: AppServices` is a constructor argument), not just
	direct references to a name in scope.
	"""
	try:
		client = await get_client()
		locations = await client.definition(file_path, line, column)
	except LspRequestError as exc:
		return _format_lsp_error(exc)
	if not locations:
		return "No definition found at that position."
	return "\n\n".join(format_location(loc, WORKSPACE_ROOT) for loc in locations)


@mcp.tool()
async def references(file_path: str, line: int, column: int, include_declaration: bool = True) -> str:
	"""Find all usages of the symbol at a position across the workspace.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character.
	"""
	try:
		client = await get_client()
		locations = await client.references(file_path, line, column, include_declaration=include_declaration)
	except LspRequestError as exc:
		return _format_lsp_error(exc)
	if not locations:
		return "No references found at that position."
	return "\n\n".join(format_location(loc, WORKSPACE_ROOT) for loc in locations)


@mcp.tool()
async def search_symbol(query: str) -> str:
	"""Search the whole workspace for a symbol by name (class, function, method, etc.).

	Use this to find a symbol's file/position first, then pass that position
	to definition/references/hover for precise, type-resolved navigation.
	Returned positions use the same character-offset column convention as the
	other tools.
	"""
	try:
		client = await get_client()
		symbols = await client.workspace_symbol(query)
	except LspRequestError as exc:
		return _format_lsp_error(exc)
	if not symbols:
		return f"No symbols matching {query!r}."
	lines = []
	for sym in symbols:
		loc = sym.get("location", {})
		rng = loc.get("range", {})
		start = rng.get("start", {})
		rel = uri_to_relative(loc.get("uri", ""), WORKSPACE_ROOT)
		lines.append(f"{sym.get('name', '?')}  ({rel}:{start.get('line', 0) + 1}:{start.get('character', 0) + 1})")
	return "\n".join(lines)


@mcp.tool()
async def diagnostics(file_path: str) -> str:
	"""Get ty's type-check diagnostics (errors/warnings) for a single file."""
	try:
		client = await get_client()
		items = await client.diagnostics(file_path)
	except LspRequestError as exc:
		return _format_lsp_error(exc)
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
