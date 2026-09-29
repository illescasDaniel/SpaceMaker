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
    uv run python -m codenav_mcp.server
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp_nav_shared.errors import TOOL_ERRORS, ToolInputError, format_tool_error
from mcp_nav_shared.exclude import is_excluded
from mcp_nav_shared.format import (
	format_callers,
	format_diagnostics,
	format_location,
	format_outline,
	format_references,
	format_references_grouped,
	format_workspace_symbols,
	symbol_kind_label,
	to_symbol_tree,
	uri_to_relative,
)
from mcp_nav_shared.lsp_client import LspClient
from mcp_nav_shared.resolve import resolve_symbol
from mcp_nav_shared.workspace import resolve_source_root, resolve_workspace_root

from codenav_mcp.ty_command import resolve_ty_command


WORKSPACE_ROOT = resolve_workspace_root("CODENAV_MCP_WORKSPACE")
# Root for import-path derivation and implementations' workspace-wide class
# scan. Defaults to the whole workspace; set CODENAV_MCP_SOURCE_ROOT (e.g. to
# "src") in a project's MCP config to scope/speed up the scan.
SOURCE_ROOT = resolve_source_root("CODENAV_MCP_SOURCE_ROOT", WORKSPACE_ROOT)

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
		"matching. Python files only (.py/.pyi) — other extensions are rejected. "
		"Start with symbol_info (what is X, where is it used) or outline (what's "
		"in this file) rather than chaining search_symbol → hover → definition → "
		"references by hand; drop to the position tools (hover/definition/"
		"references) once you have a specific line to inspect. " + _POSITION_NOTE
	),
)

_PYTHON_EXTENSIONS = {".py", ".pyi"}

_client: LspClient | None = None
_client_lock = asyncio.Lock()


def _check_python_file(file_path: str) -> None:
	"""ty only understands Python; without this, asking it to type-check or
	navigate a non-Python file (e.g. diagnostics on a README) silently
	mis-parses the file as Python instead of failing clearly."""
	suffix = Path(file_path).suffix.lower()
	if suffix not in _PYTHON_EXTENSIONS:
		raise ToolInputError(f"codenav only supports Python files (.py/.pyi), got {file_path!r}")


async def get_client() -> LspClient:
	global _client
	async with _client_lock:
		if _client is None or not _client.is_alive:
			_client = LspClient(
				workspace_root=WORKSPACE_ROOT,
				command=resolve_ty_command(WORKSPACE_ROOT),
				language_id="python",
			)
			await _client.start()
		return _client


def _format_hover_contents(contents: Any) -> str:
	if not contents:
		return ""
	if isinstance(contents, dict):
		return contents.get("value", str(contents)).strip()
	if isinstance(contents, list):
		return "\n".join(c.get("value", str(c)) if isinstance(c, dict) else str(c) for c in contents).strip()
	return str(contents).strip()


@mcp.tool()
async def hover(file_path: str, line: int, column: int) -> str:
	"""Get type/documentation info for the symbol at a position.

	`line` and `column` are 1-indexed. `column` is a UTF-16 character offset
	on the line (not a visual/display column): a leading tab counts as one
	character.
	"""
	try:
		_check_python_file(file_path)
		client = await get_client()
		result = await client.hover(file_path, line, column)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	return _format_hover_contents(result.get("contents")) or "No hover information at that position."


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
		_check_python_file(file_path)
		client = await get_client()
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
	character.
	"""
	try:
		_check_python_file(file_path)
		client = await get_client()
		locations = await client.references(file_path, line, column, include_declaration=include_declaration)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	return format_references(locations, WORKSPACE_ROOT)


@mcp.tool()
async def search_symbol(query: str) -> str:
	"""Search the whole workspace for a symbol by name (class, function, method, etc.).

	Use this to find a symbol's file/position first, then pass that position
	to definition/references/hover for precise, type-resolved navigation.
	Returned positions point at the identifier name (not the `class`/`def`
	keyword) and use the same character-offset column convention as the
	other tools. Results include a SymbolKind label and are capped.
	"""
	try:
		client = await get_client()
		symbols = await client.workspace_symbol(query)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	if not symbols:
		return f"No symbols matching {query!r}."
	return format_workspace_symbols(symbols, WORKSPACE_ROOT, query=query)


@mcp.tool()
async def diagnostics(file_path: str) -> str:
	"""Get ty's type-check diagnostics (errors/warnings) for a single file."""
	try:
		_check_python_file(file_path)
		client = await get_client()
		items = await client.diagnostics(file_path)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	return format_diagnostics(items)


@mcp.tool()
async def symbol_info(name: str, file_path: str | None = None, include_references: bool = True) -> str:
	"""One-call summary for a name: header, hover text, definition, and
	references grouped by file — the usual first lookup ("what is X",
	"where is X used") instead of chaining search_symbol → hover →
	definition → references by hand.

	`name` is a symbol name, or a dotted `Class.method` to resolve a specific
	method when the plain name is ambiguous. Pass `file_path` (relative to the
	workspace root) to disambiguate when several symbols share a name
	elsewhere in the workspace; if it's still ambiguous, the candidates are
	listed back so you can retry with a narrower name or file_path.
	"""
	try:
		client = await get_client()
		resolved = await resolve_symbol(client, WORKSPACE_ROOT, name, file_path=file_path)
		rel_path = uri_to_relative(resolved.uri, WORKSPACE_ROOT)
		line, column = resolved.line + 1, resolved.column + 1
		hover_result = await client.hover(rel_path, line, column)
		definition_locations = await client.definition(rel_path, line, column)
		reference_locations = await client.references(rel_path, line, column) if include_references else []
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	header = f"{resolved.name}  [{symbol_kind_label(resolved.kind)}]  ({rel_path}:{line}:{column})"
	hover_text = _format_hover_contents(hover_result.get("contents")) or "No hover information."
	definition_text = (
		"\n\n".join(format_location(loc, WORKSPACE_ROOT) for loc in definition_locations)
		if definition_locations
		else "No definition found."
	)
	parts = [header, "", hover_text, "", "Definition:", definition_text]
	if include_references:
		parts += ["", "References:", format_references_grouped(reference_locations, WORKSPACE_ROOT)]
	return "\n".join(parts)


@mcp.tool()
async def outline(file_path: str) -> str:
	"""Indented outline (classes, methods, functions, with line numbers) of a
	Python file, so you can navigate a large file without reading it in full.
	Follow up with hover/definition/references at a listed line, or
	symbol_info by name.
	"""
	try:
		_check_python_file(file_path)
		client = await get_client()
		symbols = await client.document_symbol(file_path)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	return format_outline(symbols)


@mcp.tool()
async def callers(name: str, file_path: str | None = None) -> str:
	"""Who calls this function/method — narrower than references, since it
	leaves out imports and type-only usages and only lists actual call sites.

	`name` resolves the same way as symbol_info (dotted Class.method accepted;
	pass file_path to disambiguate a common name).
	"""
	try:
		client = await get_client()
		resolved = await resolve_symbol(client, WORKSPACE_ROOT, name, file_path=file_path)
		rel_path = uri_to_relative(resolved.uri, WORKSPACE_ROOT)
		items = await client.prepare_call_hierarchy(rel_path, resolved.line + 1, resolved.column + 1)
		if not items:
			return f"{resolved.name} has no call hierarchy entry at that position (it may not be a callable)."
		incoming = await client.incoming_calls(items[0])
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	return format_callers(incoming, WORKSPACE_ROOT)


def _module_path(abs_path: Path) -> str:
	"""Dotted import path for a file under `SOURCE_ROOT`."""
	try:
		rel = abs_path.relative_to(SOURCE_ROOT)
	except ValueError as exc:
		raise ToolInputError(
			f"{abs_path} is outside the source root ({SOURCE_ROOT}); "
			"set CODENAV_MCP_SOURCE_ROOT if this project's importable code "
			"lives under a different directory."
		) from exc
	parts = rel.with_suffix("").parts
	if parts and parts[-1] == "__init__":
		parts = parts[:-1]
	if not parts:
		raise ToolInputError(f"cannot derive an import path for {abs_path}")
	return ".".join(parts)


def _is_protocol_base(base: ast.expr) -> bool:
	"""`Protocol`, `typing.Protocol`/`typing_extensions.Protocol`, or a
	subscripted `Protocol[T]` — `documentSymbol` doesn't expose base classes,
	so `implementations` parses the source directly to tell a Protocol port
	apart from an ordinary class."""
	if isinstance(base, ast.Subscript):
		base = base.value
	if isinstance(base, ast.Name):
		return base.id == "Protocol"
	if isinstance(base, ast.Attribute):
		return base.attr == "Protocol"
	return False


def _protocol_class_names(source: str) -> set[str]:
	"""Names of every class in `source` (at any nesting level) that subclasses
	`Protocol`."""
	try:
		tree = ast.parse(source)
	except SyntaxError:
		return set()
	return {
		node.name
		for node in ast.walk(tree)
		if isinstance(node, ast.ClassDef) and any(_is_protocol_base(base) for base in node.bases)
	}


# path -> ((mtime_ns, size), protocol class names): a pure function of the
# file's own text, so the stat pair is a sufficient key. Parsing every file's
# AST dominated `implementations`' warm cost before this.
_protocol_names_cache: dict[Path, tuple[tuple[int, int], set[str]]] = {}


def _cached_protocol_class_names(path: Path) -> set[str]:
	stat = path.stat()
	key = (stat.st_mtime_ns, stat.st_size)
	hit = _protocol_names_cache.get(path)
	if hit is not None and hit[0] == key:
		return hit[1]
	names = _protocol_class_names(path.read_text(encoding="utf-8"))
	_protocol_names_cache[path] = (key, names)
	return names


def _method_names(cls_node: dict[str, Any]) -> set[str]:
	"""Method/property names (no dunders) directly under a `to_symbol_tree` class node."""
	names: set[str] = set()
	for child in cls_node["children"]:
		if child["kind"] not in (6, 7):  # Method, Property
			continue
		name = child["name"]
		if name.startswith("__") and name.endswith("__"):
			continue
		names.add(name)
	return names


_PROBE_RELATIVE_PATH = Path("mcp-servers") / ".codenav_probe.py"


def _probe_source(port_module: str, port_name: str, candidate_module: str, candidate_name: str) -> str:
	imports = f"from {port_module} import {port_name}\n"
	if candidate_module != port_module:
		imports += f"from {candidate_module} import {candidate_name}\n"
	return f"{imports}\n\ndef _p(x: {candidate_name}) -> {port_name}:\n\treturn x\n"


# A probe verdict depends on the port and candidate files *and* whatever they
# import, so it can only be reused while nothing under SOURCE_ROOT has changed:
# the whole cache is keyed to one (path, mtime_ns, size) signature of every
# candidate file and dropped wholesale when it differs. Verdicts are keyed by
# (port module, port name, candidate module, class name) -> (verified?, line).
_probe_cache: dict[tuple[str, str, str, str], tuple[bool, str]] = {}
_probe_cache_signature: tuple[tuple[str, int, int], ...] = ()


def _source_signature(files: list[Path]) -> tuple[tuple[str, int, int], ...]:
	entries: list[tuple[str, int, int]] = []
	for path in files:
		try:
			stat = path.stat()
		except OSError:
			continue
		entries.append((str(path), stat.st_mtime_ns, stat.st_size))
	return tuple(entries)


@mcp.tool()
async def implementations(port_name: str) -> str:
	"""Find concrete classes that structurally satisfy a `Protocol` port.

	Many hexagonal codebases define ports as `Protocol`s that adapters never
	subclass explicitly, so ty's own `implementation`/`typeHierarchy` return
	nothing for them. This scans classes under SOURCE_ROOT (the whole
	workspace by default; see CODENAV_MCP_SOURCE_ROOT) whose method names
	cover the protocol's, then verifies each candidate with ty's real type
	checker via an in-memory probe file (never written to disk) — so a
	result means "assignable", not just "same method names". `port_name`
	must itself resolve to a `Protocol` class; other classes' subclasses are
	better found with `references`/`symbol_info`.
	"""
	try:
		client = await get_client()
		port = await resolve_symbol(client, WORKSPACE_ROOT, port_name)
		port_rel_path = uri_to_relative(port.uri, WORKSPACE_ROOT)
		port_symbols = await client.document_symbol(port_rel_path)
		port_source = (WORKSPACE_ROOT / port_rel_path).read_text(encoding="utf-8")
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	if port.name not in _protocol_class_names(port_source):
		return (
			f"{port.name!r} is not a Protocol; implementations only finds structural "
			"implementers of Protocol ports (use symbol_info/references for explicit subclasses)."
		)
	port_class = next(
		(n for n in to_symbol_tree(port_symbols) if n["kind"] == 5 and n["name"] == port.name),  # Class
		None,
	)
	if port_class is None:
		return f"{port_name!r} did not resolve to a class in {port_rel_path}."
	port_method_names = _method_names(port_class)
	if not port_method_names:
		return f"{port.name} has no methods to match candidates against."

	try:
		port_module = _module_path(WORKSPACE_ROOT / port_rel_path)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)

	# Vendored/generated/virtualenv trees are never this project's own source
	# and can be enormous (a `.venv` alone can dwarf the real codebase) — skip
	# them outright rather than walking (and failing to decode) thousands of
	# irrelevant files.
	all_candidate_files = sorted(p for p in SOURCE_ROOT.rglob("*.py") if not is_excluded(p, SOURCE_ROOT))
	port_abs_path = (WORKSPACE_ROOT / port_rel_path).resolve()
	# Sequential, not `asyncio.gather`: firing ~90 concurrent documentSymbol
	# requests at ty made it respond with a "content modified" LSP error;
	# sequential stays fast (under a second for this codebase's size). Each
	# file is fetched independently (not one list comprehension) so a single
	# unreadable/undecodable candidate (binary file mis-suffixed `.py`,
	# permission error, …) is skipped rather than aborting the whole scan.
	candidate_files: list[Path] = []
	symbol_lists: list[list[dict[str, Any]]] = []
	unreadable: list[Path] = []
	for path in all_candidate_files:
		try:
			symbols = await client.document_symbol(str(path))
		except TOOL_ERRORS:
			unreadable.append(path)
			continue
		candidate_files.append(path)
		symbol_lists.append(symbols)

	name_matches: list[tuple[Path, str, str]] = []  # (path, class name, module path)
	for path, symbols in zip(candidate_files, symbol_lists, strict=True):
		try:
			other_protocols = _cached_protocol_class_names(path)
		except (OSError, UnicodeDecodeError):
			unreadable.append(path)
			continue
		for cls_node in (n for n in to_symbol_tree(symbols) if n["kind"] == 5):
			if path.resolve() == port_abs_path and cls_node["name"] == port.name:
				continue  # the port never "implements" itself
			if cls_node["name"] in other_protocols:
				continue  # another Protocol, not a concrete implementer
			try:
				candidate_module = _module_path(path)
			except ToolInputError:
				continue  # outside SOURCE_ROOT's import-path derivation; can't probe it
			if port_method_names <= _method_names(cls_node):
				name_matches.append((path, cls_node["name"], candidate_module))

	skipped_note = f" ({len(unreadable)} file(s) under {SOURCE_ROOT} skipped: unreadable)" if unreadable else ""
	if not name_matches:
		return (
			f"No classes under {SOURCE_ROOT} cover {port.name}'s methods: "
			f"{', '.join(sorted(port_method_names))}.{skipped_note}"
		)

	global _probe_cache_signature
	signature = _source_signature(all_candidate_files)
	if signature != _probe_cache_signature:
		_probe_cache.clear()
		_probe_cache_signature = signature

	probe_uri = (WORKSPACE_ROOT / _PROBE_RELATIVE_PATH).as_uri()
	verified: list[str] = []
	unverified: list[str] = []
	opened = False
	try:
		for path, cls_name, candidate_module in name_matches:
			cache_key = (port_module, port.name, candidate_module, cls_name)
			rel = uri_to_relative(path.as_uri(), WORKSPACE_ROOT)
			cached = _probe_cache.get(cache_key)
			if cached is not None:
				(verified if cached[0] else unverified).append(cached[1])
				continue
			code = _probe_source(port_module, port.name, candidate_module, cls_name)
			if not opened:
				await client.open_scratch_document(probe_uri, code)
				opened = True
			else:
				await client.change_scratch_document(probe_uri, code)
			items = await client.pull_diagnostics(probe_uri)
			# Verified means the probe document has *no* diagnostics at all —
			# not just none tagged `invalid-return-type`. A candidate module
			# that fails to import (e.g. it lives outside where its own
			# import path resolves, a common miss when SOURCE_ROOT doesn't
			# match the project's real package layout) produces an
			# `unresolved-import` diagnostic instead, and with only the
			# narrower check that case was silently counted as verified even
			# though ty never actually checked the assignment.
			if not items:
				line, is_verified = f"{cls_name}  ({rel})", True
			elif any(item.get("code") == "invalid-return-type" for item in items):
				line = f"{cls_name}  ({rel})  — method names match but ty rejects the assignment"
				is_verified = False
			else:
				reasons = "; ".join(str(item.get("message", "")).splitlines()[0] for item in items[:3])
				line = f"{cls_name}  ({rel})  — could not verify: {reasons}"
				is_verified = False
			_probe_cache[cache_key] = (is_verified, line)
			(verified if is_verified else unverified).append(line)
	except TOOL_ERRORS as exc:
		return format_tool_error(exc)
	finally:
		if opened:
			await client.close_scratch_document(probe_uri)

	lines = [f"{len(verified)} class(es) implement {port.name} (type-verified):{skipped_note}"]
	lines += verified or ["(none)"]
	if unverified:
		lines += ["", "Method-name matches that don't type-check as the port:"]
		lines += unverified
	return "\n".join(lines)


if __name__ == "__main__":
	mcp.run(transport="stdio")
