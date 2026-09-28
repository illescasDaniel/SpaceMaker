"""webnav: MCP server exposing JS/HTML/CSS language-server features (hover,
definition, references, workspace symbol search, diagnostics) plus a
workspace-wide CSS custom-property/selector index (css_var, selector) as
MCP tools.

Multiplexes three Node-based language servers behind one MCP tool set,
routed by file extension: `typescript-language-server` for `.js`/`.mjs`/
`.cjs` (via `allowJs`, no TypeScript required), and `vscode-html-language-
server`/`vscode-css-language-server` (from `vscode-langservers-extracted`)
for `.html`/`.css`. Mirrors codenav_mcp's shape and its shared
`_shared.lsp_client.LspClient`; see docs/agent-tooling.md for details.

Run standalone for manual testing:
    uv run python -m webnav_mcp.server
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from _shared.errors import TOOL_ERRORS, ToolInputError, format_tool_error
from _shared.format import (
	format_diagnostics,
	format_location,
	format_references,
	format_workspace_symbols,
)
from _shared.lsp_client import LspClient
from _shared.workspace import resolve_workspace_root
from mcp.server.mcpserver import MCPServer
from webnav_mcp import web_index
from webnav_mcp.lang_command import resolve_css_command, resolve_html_command, resolve_ts_command


WORKSPACE_ROOT = resolve_workspace_root("WEBNAV_MCP_WORKSPACE")

# One or more `label=relative/path` roots to index separately (see
# web_index.build_workspace_index); e.g. splitting production assets from
# design wireframes. Unset means "index the whole workspace as one root" —
# most projects have no such split and don't need to set this.
_raw_web_roots = os.environ.get("WEBNAV_MCP_ROOTS")
WEB_ROOTS = web_index.parse_roots_env(_raw_web_roots, WORKSPACE_ROOT) if _raw_web_roots else None

_POSITION_NOTE = (
	"Positions are 1-indexed. `column` is a UTF-16 character offset on the "
	"line (not a visual/display column): a leading tab counts as one "
	"character, so after a single tab the next character starts at column 2."
)

mcp = MCPServer(
	name="webnav",
	instructions=(
		"Code navigation for this project's JS/HTML/CSS, backed by "
		"typescript-language-server (JS) and vscode-langservers-extracted "
		"(HTML/CSS). Prefer this over grepping for symbol definitions/usages. "
		"search_symbol only covers JS (the HTML/CSS servers don't implement "
		"useful workspace-wide symbol search). The language servers only see "
		"one file at a time, so `--custom-properties` and `#id`/`.class` "
		"selectors can't be cross-referenced across files that way; use "
		"css_var/selector for those instead of hover/definition/references — "
		"references and definition also answer from that same cross-file "
		"index automatically when the position is on one of those tokens in "
		"a .css/.html file. " + _POSITION_NOTE
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
		if _ts_client is None or not _ts_client.is_alive:
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
		if _html_client is None or not _html_client.is_alive:
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
		if _css_client is None or not _css_client.is_alive:
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
	raise ToolInputError(f"webnav has no language server for {file_path!r} (supported: .js/.mjs/.cjs/.html/.css)")


def _resolve_path(file_path: str) -> Path:
	p = Path(file_path)
	return p if p.is_absolute() else WORKSPACE_ROOT / p


def _index_token_at(file_path: str, line: int, column: int) -> str | None:
	"""The `--var`/`#id`/`.class` token at a position in a `.css`/`.html`
	file, so `references`/`definition` can answer from the cross-file index
	instead of the single-file language server (see module docstring)."""
	if Path(file_path).suffix.lower() not in (".css", ".html"):
		return None
	try:
		text_line = _resolve_path(file_path).read_text(encoding="utf-8").splitlines()[line - 1]
	except (OSError, IndexError):
		return None
	return web_index.token_at_position(text_line, column)


def _index_answer(token: str) -> str:
	indexes = web_index.build_workspace_index(WORKSPACE_ROOT, WEB_ROOTS)
	if token.startswith("--"):
		return web_index.format_css_var(indexes, token)
	return web_index.format_selector(indexes, token)


@mcp.tool()
async def hover(file_path: str, line: int, column: int) -> str:
	"""Get type/documentation info for the symbol at a position.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character.
	"""
	try:
		client = await _client_for(file_path)
		result = await client.hover(file_path, line, column)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	contents = result.get("contents")
	if not contents:
		return "No hover information at that position."
	if isinstance(contents, dict):
		return contents.get("value", str(contents)).strip()
	if isinstance(contents, list):
		return "\n".join(c.get("value", str(c)) if isinstance(c, dict) else str(c) for c in contents).strip()
	return str(contents).strip()


@mcp.tool()
async def definition(file_path: str, line: int, column: int) -> str:
	"""Go to the definition of the symbol at a position.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character. On a `--custom-property`/`#id`/`.class` token in a `.css`/
	`.html` file, answers from the cross-file index (see css_var/selector)
	instead of the single-file language server.
	"""
	token = _index_token_at(file_path, line, column)
	if token is not None:
		return _index_answer(token)
	try:
		client = await _client_for(file_path)
		locations = await client.definition(file_path, line, column)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	if not locations:
		return "No definition found at that position."
	return "\n\n".join(format_location(loc, WORKSPACE_ROOT) for loc in locations)


@mcp.tool()
async def references(file_path: str, line: int, column: int, include_declaration: bool = True) -> str:
	"""Find all usages of the symbol at a position across the workspace.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character. On a `--custom-property`/`#id`/`.class` token in a `.css`/
	`.html` file, answers from the cross-file index (see css_var/selector)
	instead of the single-file language server.
	"""
	token = _index_token_at(file_path, line, column)
	if token is not None:
		return _index_answer(token)
	try:
		client = await _client_for(file_path)
		locations = await client.references(file_path, line, column, include_declaration=include_declaration)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	return format_references(locations, WORKSPACE_ROOT)


@mcp.tool()
async def search_symbol(query: str) -> str:
	"""Search JS files for a symbol by name (function, class, const, etc.).

	JS-only: the HTML/CSS language servers don't implement useful
	workspace-wide symbol search (webnav does not reimplement it). Use this
	to find a symbol's file/position first, then pass that position to
	definition/references/hover. Returned positions point at the identifier
	name and use the same character-offset column convention as the other
	tools. Results include a SymbolKind label and are capped.
	"""
	try:
		client = await _get_ts_client()
		symbols = await client.workspace_symbol(query)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	if not symbols:
		return f"No symbols matching {query!r}."
	return format_workspace_symbols(symbols, WORKSPACE_ROOT, query=query)


@mcp.tool()
async def diagnostics(file_path: str) -> str:
	"""Get the relevant language server's diagnostics (errors/warnings) for a single file.

	For `.css`/`.html` files, this also includes index-derived warnings the
	single-file language server can't see: `var(--x)` used with no matching
	declaration anywhere in the same indexed root, and CSS selectors
	(`#id`/`.class`) with no HTML/JS reference in that root.
	"""
	try:
		client = await _client_for(file_path)
		items = await client.diagnostics(file_path)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	lines = [format_diagnostics(items)]
	if Path(file_path).suffix.lower() in (".css", ".html"):
		located = web_index.root_index_for_file(
			web_index.build_workspace_index(WORKSPACE_ROOT, WEB_ROOTS), _resolve_path(file_path)
		)
		if located is not None:
			idx, file_rel = located
			extra = web_index.diagnostics_for_file(idx, file_rel)
			if extra:
				lines.append("\n".join(extra))
	combined = [text for text in lines if text and text != "No diagnostics."]
	return "\n".join(combined) if combined else "No diagnostics."


@mcp.tool()
async def css_var(name: str) -> str:
	"""Look up a `--custom-property` across the whole workspace.

	The CSS/HTML language servers only see one file at a time, so `var(--x)`
	usages can't be cross-referenced across files that way — this scans
	`.css` files and HTML `<style>`/`style="…"` blocks/attributes instead.
	`name` may be given with or without the leading `--`. Definitions (value
	+ enclosing context, e.g. `@media (prefers-color-scheme: dark) › :root`)
	and usages (grouped by file with line numbers) are reported separately per
	configured root (see `WEBNAV_MCP_ROOTS`; a single unnamed root by default),
	since each may define its own values.
	"""
	indexes = web_index.build_workspace_index(WORKSPACE_ROOT, WEB_ROOTS)
	return web_index.format_css_var(indexes, name)


@mcp.tool()
async def selector(name: str) -> str:
	"""Look up a `#id` or `.class` selector across the whole workspace.

	Cross-references CSS rule definitions, HTML `id=`/`class=` attributes,
	and JS usages (`getElementById`, `classList.add/remove/toggle/contains`,
	`querySelector`/`querySelectorAll`, `className` assignment) — something
	the single-file CSS/HTML language servers can't do. `name` must include
	the leading `#` or `.`. Grouped by file with line numbers, separately per
	configured root (see `WEBNAV_MCP_ROOTS`). A JS hit built from string
	concatenation (e.g. `getElementById("view-" + x)`) is reported against
	only its static prefix and labeled "dynamic partial match"; a query whose
	name starts with such a prefix (e.g. `#view-components` against a stored
	`#view-`) also surfaces that hit, labeled "dynamic partial match via
	'<prefix>'", instead of being silently dropped or guessed.
	"""
	indexes = web_index.build_workspace_index(WORKSPACE_ROOT, WEB_ROOTS)
	return web_index.format_selector(indexes, name)


if __name__ == "__main__":
	mcp.run(transport="stdio")
