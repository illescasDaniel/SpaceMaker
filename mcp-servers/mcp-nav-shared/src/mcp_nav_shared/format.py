"""Shared formatting helpers for codenav/webnav MCP tool responses."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


# LSP SymbolKind (https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#symbolKind)
_SYMBOL_KINDS: dict[int, str] = {
	1: "File",
	2: "Module",
	3: "Namespace",
	4: "Package",
	5: "Class",
	6: "Method",
	7: "Property",
	8: "Field",
	9: "Constructor",
	10: "Enum",
	11: "Interface",
	12: "Function",
	13: "Variable",
	14: "Constant",
	15: "String",
	16: "Number",
	17: "Boolean",
	18: "Array",
	19: "Object",
	20: "Key",
	21: "Null",
	22: "EnumMember",
	23: "Struct",
	24: "Event",
	25: "Operator",
	26: "TypeParameter",
}

DEFAULT_SEARCH_SYMBOL_LIMIT = 50
DEFAULT_DIAGNOSTICS_LIMIT = 200
# When the LSP range starts on a decorator line (or is a single-line decorator
# span), walk this many lines past start to find the identifier.
_NAME_LOOKAHEAD_LINES = 8

# LSP DiagnosticSeverity (same spec as SymbolKind above).
_DIAGNOSTIC_SEVERITIES: dict[int, str] = {1: "error", 2: "warning", 3: "info", 4: "hint"}


def uri_to_path(uri: str) -> Path:
	parsed = urlparse(uri)
	return Path(unquote(parsed.path.lstrip("/") if os.name == "nt" else parsed.path))


def uri_to_relative(uri: str, workspace_root: Path) -> str:
	path = uri_to_path(uri)
	try:
		return str(path.relative_to(workspace_root)).replace("\\", "/")
	except ValueError:
		return str(path)


def snippet(uri: str, start_line: int, end_line: int, *, context: int = 0) -> str:
	path = uri_to_path(uri)
	try:
		lines = path.read_text(encoding="utf-8").splitlines()
	except OSError:
		return ""
	lo = max(0, start_line - context)
	hi = min(len(lines), end_line + 1 + context)
	numbered = [f"{i + 1:>5} | {lines[i]}" for i in range(lo, hi)]
	return "\n".join(numbered)


def _location_range(loc: dict[str, Any]) -> dict[str, Any]:
	"""Prefer LocationLink selection range when present (narrower symbol span)."""
	if "targetSelectionRange" in loc:
		return loc["targetSelectionRange"] or {}
	return loc.get("range") or loc.get("targetRange") or {}


def format_location(loc: dict[str, Any], workspace_root: Path) -> str:
	uri = loc.get("uri") or loc.get("targetUri", "")
	rng = _location_range(loc)
	start = rng.get("start", {})
	end = rng.get("end", {})
	start_line = start.get("line", 0)
	start_col = start.get("character", 0)
	end_line = end.get("line", start_line)
	rel = uri_to_relative(uri, workspace_root)
	header = f"{rel}:{start_line + 1}:{start_col + 1}"
	body = snippet(uri, start_line, end_line, context=2)
	return f"{header}\n{body}" if body else header


def symbol_kind_label(kind: Any) -> str:
	if isinstance(kind, int):
		return _SYMBOL_KINDS.get(kind, f"Kind{kind}")
	return "?"


def _name_position(
	uri: str,
	name: str,
	start_line: int,
	start_col: int,
	end_line: int | None = None,
) -> tuple[int, int]:
	"""0-based (line, character) for `name` near the LSP range, else range start.

	Searches the range lines first, then up to `_NAME_LOOKAHEAD_LINES` past
	`start_line`, so decorator-only starts (e.g. `@dataclass` then `class Foo`)
	still resolve to the identifier.
	"""
	if not name:
		return start_line, start_col
	path = uri_to_path(uri)
	try:
		lines = path.read_text(encoding="utf-8").splitlines()
	except OSError:
		return start_line, start_col
	if start_line < 0 or start_line >= len(lines):
		return start_line, start_col

	range_end = start_line if end_line is None else max(start_line, end_line)
	hi = max(range_end, start_line + _NAME_LOOKAHEAD_LINES)
	hi = min(hi, len(lines) - 1)

	for line_no in range(start_line, hi + 1):
		line = lines[line_no]
		if line_no == start_line:
			# Skip keywords (class/def/function) that often begin the range.
			idx = line.find(name, max(0, start_col))
			if idx < 0:
				idx = line.find(name)
		else:
			idx = line.find(name)
		if idx >= 0:
			return line_no, idx
	return start_line, start_col


def workspace_symbol_position(sym: dict[str, Any]) -> tuple[str, int, int]:
	"""Return (uri, 0-based line, 0-based character) aimed at the symbol name.

	Preference: selectionRange → name within range/lookahead → range.start.
	ty often returns SymbolInformation ranges that start at `class`/`def` or
	on a decorator line; agents need the identifier for hover/definition/references.
	"""
	loc = sym.get("location") or {}
	uri = loc.get("uri", "")
	sel = sym.get("selectionRange") or {}
	if sel.get("start"):
		start = sel["start"]
		return uri, int(start.get("line", 0)), int(start.get("character", 0))
	rng = loc.get("range") or {}
	start = rng.get("start") or {}
	end = rng.get("end") or {}
	start_line = int(start.get("line", 0))
	start_col = int(start.get("character", 0))
	end_line = int(end["line"]) if "line" in end else None
	name = str(sym.get("name") or "")
	line, col = _name_position(uri, name, start_line, start_col, end_line)
	return uri, line, col


def format_workspace_symbol(sym: dict[str, Any], workspace_root: Path) -> str:
	name = str(sym.get("name") or "?")
	kind = symbol_kind_label(sym.get("kind"))
	uri, line, col = workspace_symbol_position(sym)
	rel = uri_to_relative(uri, workspace_root) if uri else "?"
	return f"{name}  [{kind}]  ({rel}:{line + 1}:{col + 1})"


def _match_tier(name: str, query: str) -> int:
	if name == query:
		return 0
	folded_name, folded_query = name.casefold(), query.casefold()
	if folded_name == folded_query:
		return 1
	if folded_name.startswith(folded_query):
		return 2
	if folded_query in folded_name:
		return 3
	return 4


def rank_workspace_symbols(symbols: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
	"""Exact → case-insensitive exact → prefix → substring → other (stable within a tier).

	ty's workspace/symbol is fuzzy (`LspClient` also matches long test names
	containing those letters in order) and returns hits in workspace order, so
	without ranking the exact match can land past the result cap.
	"""
	if not query:
		return list(symbols)
	return sorted(symbols, key=lambda sym: _match_tier(str(sym.get("name") or ""), query))


def format_workspace_symbols(
	symbols: list[dict[str, Any]],
	workspace_root: Path,
	*,
	query: str = "",
	limit: int = DEFAULT_SEARCH_SYMBOL_LIMIT,
) -> str:
	if not symbols:
		return ""
	shown = rank_workspace_symbols(symbols, query)[: max(0, limit)]
	lines = [format_workspace_symbol(sym, workspace_root) for sym in shown]
	omitted = len(symbols) - len(shown)
	if omitted > 0:
		lines.append(f"… and {omitted} more (showing first {len(shown)})")
	return "\n".join(lines)


def format_diagnostic(item: dict[str, Any]) -> str:
	"""One diagnostic as `L:C [severity code] first line`, with any further
	message lines (e.g. ty's `Code is unreachable` / `This may depend on your
	current environment and settings` two-liner) indented on their own lines
	so every line that doesn't start with whitespace is exactly one diagnostic."""
	rng = item.get("range") or {}
	start = rng.get("start") or {}
	severity = _DIAGNOSTIC_SEVERITIES.get(item.get("severity"), "?")
	code = item.get("code")
	tag = f"{severity} {code}" if code not in (None, "") else severity
	lines = str(item.get("message", "")).splitlines() or [""]
	header = f"{start.get('line', 0) + 1}:{start.get('character', 0) + 1} [{tag}] {lines[0]}"
	return "\n".join([header, *(f"    {line}" for line in lines[1:])])


def format_diagnostics(items: list[dict[str, Any]], *, limit: int = DEFAULT_DIAGNOSTICS_LIMIT) -> str:
	"""Format LSP diagnostics, capped like `format_workspace_symbols` so a badly
	broken file (or one mis-parsed as the wrong language) can't flood the
	caller with an unbounded wall of text."""
	if not items:
		return "No diagnostics."
	shown = items[: max(0, limit)]
	lines = [format_diagnostic(item) for item in shown]
	omitted = len(items) - len(shown)
	if omitted > 0:
		lines.append(f"… and {omitted} more (showing first {len(shown)})")
	return "\n".join(lines)


DEFAULT_REFERENCE_FILE_LIMIT = 25


def format_references_grouped(
	locations: list[dict[str, Any]],
	workspace_root: Path,
	*,
	file_limit: int = DEFAULT_REFERENCE_FILE_LIMIT,
	with_columns: bool = False,
) -> str:
	"""Compact `path: L12, L40, …` grouping (no snippets) for `symbol_info`, where
	full per-location snippets (as `format_location` gives `references`) would
	make a one-call summary too long to be useful.

	`with_columns=True` (used by `format_references`'s compact fallback) keeps
	the column alongside each line (`L12:4`) so a follow-up position-based call
	(hover/definition) can still target the hit precisely."""
	if not locations:
		return "No references found."
	groups: dict[str, set[tuple[int, int]]] = {}
	for loc in locations:
		uri = loc.get("uri") or loc.get("targetUri", "")
		rng = _location_range(loc)
		start = rng.get("start") or {}
		start_line = int(start.get("line", 0)) + 1
		start_col = int(start.get("character", 0)) + 1
		rel = uri_to_relative(uri, workspace_root)
		groups.setdefault(rel, set()).add((start_line, start_col))
	total = sum(len(nums) for nums in groups.values())
	files = sorted(groups.items())
	shown = files[:file_limit]

	def _tag(line: int, col: int) -> str:
		return f"L{line}:{col}" if with_columns else f"L{line}"

	lines = [f"{total} reference(s) in {len(files)} file(s):"]
	lines += [f"{path}: " + ", ".join(_tag(n, c) for n, c in sorted(nums)) for path, nums in shown]
	omitted = len(files) - len(shown)
	if omitted > 0:
		lines.append(f"… and {omitted} more file(s)")
	return "\n".join(lines)


DEFAULT_REFERENCES_SNIPPET_LIMIT = 8


def format_references(
	locations: list[dict[str, Any]],
	workspace_root: Path,
	*,
	snippet_limit: int = DEFAULT_REFERENCES_SNIPPET_LIMIT,
) -> str:
	"""Full per-location snippets (`format_location`) for a small number of
	hits; above `snippet_limit`, falls back to the compact grouped listing
	(`format_references_grouped`, with columns) so a symbol like `showView`
	with 20+ call sites doesn't flood the reply with 100+ lines of context."""
	if not locations:
		return "No references found at that position."
	if len(locations) <= snippet_limit:
		return "\n\n".join(format_location(loc, workspace_root) for loc in locations)
	grouped = format_references_grouped(locations, workspace_root, with_columns=True)
	return f"(compact list: {len(locations)} > {snippet_limit} hits)\n{grouped}"


def is_hierarchical_document_symbols(symbols: list[dict[str, Any]]) -> bool:
	"""A server offered `hierarchicalDocumentSymbolSupport` (`mcp_nav_shared/lsp_client.py`
	declares it in `initialize`) returns nested `DocumentSymbol` (a `range`/
	`selectionRange` pair directly on the symbol, optional `children`) instead
	of flat `SymbolInformation` (a `location` field)."""
	return bool(symbols) and "range" in symbols[0] and "location" not in symbols[0]


def _document_symbol_node(sym: dict[str, Any]) -> dict[str, Any]:
	rng = sym.get("range") or {}
	start = rng.get("start") or {}
	end = rng.get("end") or {}
	return {
		"name": str(sym.get("name") or "?"),
		"kind": sym.get("kind"),
		"start_line": int(start.get("line", 0)),
		"end_line": int(end.get("line", start.get("line", 0))),
		"children": [_document_symbol_node(child) for child in sym.get("children") or []],
	}


def _nest_symbol_information(symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Nest ty's flat `SymbolInformation` list by range containment: sort by
	start line (widest span first among ties), then fold each symbol into the
	innermost still-open ancestor whose range contains it."""
	nodes: list[dict[str, Any]] = []
	for sym in symbols:
		loc = sym.get("location") or {}
		rng = loc.get("range") or {}
		start = rng.get("start") or {}
		end = rng.get("end") or {}
		nodes.append(
			{
				"name": str(sym.get("name") or "?"),
				"kind": sym.get("kind"),
				"start_line": int(start.get("line", 0)),
				"end_line": int(end.get("line", start.get("line", 0))),
				"children": [],
			}
		)
	nodes.sort(key=lambda n: (n["start_line"], -(n["end_line"] - n["start_line"])))
	roots: list[dict[str, Any]] = []
	stack: list[dict[str, Any]] = []
	for node in nodes:
		while stack and not (
			stack[-1]["start_line"] <= node["start_line"] and node["end_line"] <= stack[-1]["end_line"]
		):
			stack.pop()
		(stack[-1]["children"] if stack else roots).append(node)
		stack.append(node)
	return roots


def to_symbol_tree(symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
	"""Normalize either shape `documentSymbol` can return (see
	`is_hierarchical_document_symbols`) into a common node shape: `{name,
	kind, start_line, end_line, children}`, 0-based lines. Shared by
	`format_outline` and codenav's `implementations`/`symbol_info` (method-name
	matching, tree search) — one nesting implementation instead of two shape-
	specific ones scattered across callers."""
	if is_hierarchical_document_symbols(symbols):
		return [_document_symbol_node(sym) for sym in symbols]
	return _nest_symbol_information(symbols)


def format_outline(symbols: list[dict[str, Any]], *, indent: str = "  ") -> str:
	"""Indented `name  [Kind]  :start-end` tree, from either shape
	`documentSymbol` can return (see `is_hierarchical_document_symbols`).
	The end line lets an agent judge a member's size (e.g. "is this method
	worth reading in full?") without a separate call."""
	if not symbols:
		return "No symbols found."
	roots = to_symbol_tree(symbols)

	def walk(nodes: list[dict[str, Any]], depth: int) -> None:
		for node in nodes:
			kind = symbol_kind_label(node["kind"])
			start, end = node["start_line"] + 1, node["end_line"] + 1
			span = f":{start}" if start == end else f":{start}-{end}"
			lines.append(f"{indent * depth}{node['name']}  [{kind}]  {span}")
			walk(node["children"], depth + 1)

	lines: list[str] = []
	walk(roots, 0)
	return "\n".join(lines)


def format_callers(incoming_calls: list[dict[str, Any]], workspace_root: Path) -> str:
	"""`callHierarchy/incomingCalls` results as `caller  [Kind]  (path:line)
	calls at L.., L..` — the caller's own position plus every call-site line
	within it, so an agent sees who calls a function without imports/type-only
	usages mixed in (unlike `references`)."""
	if not incoming_calls:
		return "No callers found."
	lines = []
	for call in incoming_calls:
		frm = call.get("from") or {}
		name = str(frm.get("name") or "?")
		kind = symbol_kind_label(frm.get("kind"))
		rel = uri_to_relative(frm.get("uri", ""), workspace_root)
		sel_start = (frm.get("selectionRange") or {}).get("start") or {}
		caller_line = int(sel_start.get("line", 0)) + 1
		call_site_lines = sorted({int((r.get("start") or {}).get("line", 0)) + 1 for r in call.get("fromRanges") or []})
		call_sites = ", ".join(f"L{n}" for n in call_site_lines) or f"L{caller_line}"
		lines.append(f"{name}  [{kind}]  ({rel}:{caller_line}) calls at {call_sites}")
	return "\n".join(lines)
