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
# When the LSP range starts on a decorator line (or is a single-line decorator
# span), walk this many lines past start to find the identifier.
_NAME_LOOKAHEAD_LINES = 8


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
