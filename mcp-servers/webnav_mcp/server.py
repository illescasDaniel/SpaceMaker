"""webnav: MCP server exposing JS/HTML/CSS language-server features (hover,
definition, references, workspace symbol search, diagnostics) as MCP tools.

Multiplexes three Node-based language servers behind one MCP tool set,
routed by file extension: `typescript-language-server` for `.js`/`.mjs`/
`.cjs` (via `allowJs`, no TypeScript required), and `vscode-html-language-
server`/`vscode-css-language-server` (from `vscode-langservers-extracted`)
for `.html`/`.css`. Mirrors codenav_mcp's shape and its shared
`_shared.lsp_client.LspClient`; see docs/agent-tooling.md for details.

Run standalone for manual testing:
    uv run python mcp-servers/webnav_mcp/server.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _shared.lsp_client import LspClient  # noqa: E402
from lang_command import resolve_css_command, resolve_html_command, resolve_ts_command  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402


WORKSPACE_ROOT = Path(os.environ.get("WEBNAV_MCP_WORKSPACE", Path.cwd())).resolve()

mcp = MCPServer(
	name="webnav",
	instructions=(
		"Code navigation for this project's JS/HTML/CSS, backed by "
		"typescript-language-server (JS) and vscode-langservers-extracted "
		"(HTML/CSS). Prefer this over grepping for symbol definitions/usages. "
		"search_symbol only covers JS (the HTML/CSS servers don't implement "
		"useful workspace-wide symbol search)."
	),
)

_JS_EXTENSIONS = {".js", ".mjs", ".cjs"}

_ts_client: LspClient | None = None
_html_client: LspClient | None = None
_css_client: LspClient | None = None
_client_lock = asyncio.Lock()


def _js_include_globs(workspace_root: Path) -> list[str]:
	"""Read the `include` globs from jsconfig.json, so webnav's eager-open list
	stays in sync with what the ts-server itself treats as the JS project."""
	try:
		config = json.loads((workspace_root / "jsconfig.json").read_text(encoding="utf-8"))
	except (OSError, json.JSONDecodeError):
		return []
	return config.get("include", [])


async def _get_ts_client() -> LspClient:
	global _ts_client
	async with _client_lock:
		if _ts_client is None:
			_ts_client = LspClient(
				workspace_root=WORKSPACE_ROOT,
				command=resolve_ts_command(WORKSPACE_ROOT),
				language_id="javascript",
			)
			await _ts_client.start()
			# tsserver's workspace/symbol only searches files it has opened, so
			# eagerly open the whole JS project here rather than leaving the
			# first search_symbol call (agents' typical first lookup) to miss
			# every file it hasn't happened to hover/define/reference first.
			for glob in _js_include_globs(WORKSPACE_ROOT):
				for path in WORKSPACE_ROOT.glob(glob):
					await _ts_client.ensure_open(str(path))
		return _ts_client


async def _get_html_client() -> LspClient:
	global _html_client
	async with _client_lock:
		if _html_client is None:
			_html_client = LspClient(
				workspace_root=WORKSPACE_ROOT,
				command=resolve_html_command(WORKSPACE_ROOT),
				language_id="html",
			)
			await _html_client.start()
		return _html_client


async def _get_css_client() -> LspClient:
	global _css_client
	async with _client_lock:
		if _css_client is None:
			_css_client = LspClient(
				workspace_root=WORKSPACE_ROOT,
				command=resolve_css_command(WORKSPACE_ROOT),
				language_id="css",
			)
			await _css_client.start()
		return _css_client


async def _client_for(file_path: str) -> LspClient:
	suffix = Path(file_path).suffix.lower()
	if suffix in _JS_EXTENSIONS:
		return await _get_ts_client()
	if suffix == ".html":
		return await _get_html_client()
	if suffix == ".css":
		return await _get_css_client()
	raise ValueError(f"webnav has no language server for {file_path!r} (supported: .js/.mjs/.cjs/.html/.css)")


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
	client = await _client_for(file_path)
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
	"""Go to the definition of the symbol at a position (1-indexed line/column)."""
	client = await _client_for(file_path)
	locations = await client.definition(file_path, line, column)
	if not locations:
		return "No definition found at that position."
	return "\n\n".join(_format_location(loc) for loc in locations)


@mcp.tool()
async def references(file_path: str, line: int, column: int, include_declaration: bool = True) -> str:
	"""Find all usages of the symbol at a position (1-indexed line/column) across the workspace."""
	client = await _client_for(file_path)
	locations = await client.references(file_path, line, column, include_declaration=include_declaration)
	if not locations:
		return "No references found at that position."
	return "\n\n".join(_format_location(loc) for loc in locations)


@mcp.tool()
async def search_symbol(query: str) -> str:
	"""Search JS files for a symbol by name (function, class, const, etc.).

	JS-only: the HTML/CSS language servers don't implement useful
	workspace-wide symbol search. Use this to find a symbol's file/position
	first, then pass that position to definition/references/hover.
	"""
	client = await _get_ts_client()
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
	"""Get the relevant language server's diagnostics (errors/warnings) for a single file."""
	client = await _client_for(file_path)
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
