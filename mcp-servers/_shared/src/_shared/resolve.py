"""Name-based symbol resolution shared by codenav's composite tools
(`symbol_info`, `callers`, `implementations`): a `workspace_symbol` lookup
with tiered ranking, dotted `Class.method` resolution via `documentSymbol`,
and disambiguation by `file_path` — so those tools take a name instead of a
hand-computed position.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _shared.errors import ToolInputError
from _shared.format import (
	_match_tier,
	format_workspace_symbol,
	is_hierarchical_document_symbols,
	rank_workspace_symbols,
	uri_to_relative,
	workspace_symbol_position,
)
from _shared.lsp_client import LspClient


class SymbolResolutionError(ToolInputError):
	"""No single confident match for a name-based symbol query: not found, or ambiguous."""


@dataclass
class ResolvedSymbol:
	name: str
	kind: Any
	uri: str
	line: int  # 0-based, aimed at the identifier
	column: int  # 0-based
	range_start_line: int  # 0-based, the symbol's full span (for dotted member lookup)
	range_end_line: int


def _resolved_from_symbol(sym: dict[str, Any]) -> ResolvedSymbol:
	uri, line, column = workspace_symbol_position(sym)
	rng = (sym.get("location") or {}).get("range") or {}
	start_line = int((rng.get("start") or {}).get("line", line))
	end_line = int((rng.get("end") or {}).get("line", start_line))
	return ResolvedSymbol(
		name=str(sym.get("name") or "?"),
		kind=sym.get("kind"),
		uri=uri,
		line=line,
		column=column,
		range_start_line=start_line,
		range_end_line=end_line,
	)


def _member_start_line(sym: dict[str, Any]) -> int:
	rng = (sym.get("location") or {}).get("range") or {}
	return int((rng.get("start") or {}).get("line", 0))


def _find_member_node(symbols: list[dict[str, Any]], container_name: str, member_name: str) -> dict[str, Any] | None:
	"""Search hierarchical `DocumentSymbol` results for `member_name` directly
	under a node named `container_name` (searches nested classes too, in case
	`container_name` isn't top-level)."""
	for node in symbols:
		if str(node.get("name")) == container_name:
			for child in node.get("children") or []:
				if str(child.get("name")) == member_name:
					return child
		found = _find_member_node(node.get("children") or [], container_name, member_name)
		if found is not None:
			return found
	return None


def _resolved_from_hierarchical_node(member_name: str, node: dict[str, Any], uri: str) -> ResolvedSymbol:
	sel_start = (node.get("selectionRange") or {}).get("start") or (node.get("range") or {}).get("start") or {}
	rng = node.get("range") or {}
	start_line = int((rng.get("start") or {}).get("line", 0))
	end_line = int((rng.get("end") or {}).get("line", start_line))
	return ResolvedSymbol(
		name=member_name,
		kind=node.get("kind"),
		uri=uri,
		line=int(sel_start.get("line", start_line)),
		column=int(sel_start.get("character", 0)),
		range_start_line=start_line,
		range_end_line=end_line,
	)


def _format_candidates(candidates: list[dict[str, Any]], workspace_root: Path) -> str:
	return "\n".join(format_workspace_symbol(c, workspace_root) for c in candidates[:10])


def _not_found(query: str) -> SymbolResolutionError:
	return SymbolResolutionError(f"No symbol found matching {query!r}.")


def _ambiguous(query: str, candidates: list[dict[str, Any]], workspace_root: Path) -> SymbolResolutionError:
	return SymbolResolutionError(
		f"{len(candidates)} symbols match {query!r}; pass file_path to disambiguate:\n"
		f"{_format_candidates(candidates, workspace_root)}"
	)


def _matches_file(sym: dict[str, Any], workspace_root: Path, file_path: str) -> bool:
	rel = uri_to_relative((sym.get("location") or {}).get("uri", ""), workspace_root)
	target = str(Path(file_path)).replace("\\", "/")
	return rel == target or rel.endswith("/" + target) or target.endswith("/" + rel)


async def _exact_candidates(
	client: LspClient, workspace_root: Path, name: str, *, file_path: str | None
) -> list[dict[str, Any]]:
	symbols = await client.workspace_symbol(name)
	ranked = rank_workspace_symbols(symbols, name)
	exact = [s for s in ranked if _match_tier(str(s.get("name") or ""), name) <= 1]
	# Prefer a case-exact match (tier 0) over a merely case-insensitive one
	# (tier 1) when both exist, e.g. `repo_root` vs. a `REPO_ROOT` constant
	# elsewhere in the workspace — an agent asking for the lowercase name
	# almost always means the exact symbol, not an unrelated same-letters one.
	case_exact = [s for s in exact if _match_tier(str(s.get("name") or ""), name) == 0]
	if case_exact:
		exact = case_exact
	if file_path is not None:
		narrowed = [s for s in exact if _matches_file(s, workspace_root, file_path)]
		if narrowed:
			exact = narrowed
	return exact


async def _resolve_simple(
	client: LspClient, workspace_root: Path, query: str, *, file_path: str | None
) -> ResolvedSymbol:
	exact = await _exact_candidates(client, workspace_root, query, file_path=file_path)
	if not exact:
		raise _not_found(query)
	if len(exact) > 1:
		raise _ambiguous(query, exact, workspace_root)
	return _resolved_from_symbol(exact[0])


async def _resolve_dotted(
	client: LspClient, workspace_root: Path, query: str, *, file_path: str | None
) -> ResolvedSymbol:
	container_query, _, member_name = query.rpartition(".")
	container = await _resolve_simple(client, workspace_root, container_query, file_path=file_path)
	rel_path = uri_to_relative(container.uri, workspace_root)
	members = await client.document_symbol(rel_path)
	if is_hierarchical_document_symbols(members):
		node = _find_member_node(members, container.name, member_name)
		if node is None:
			raise _not_found(query)
		return _resolved_from_hierarchical_node(member_name, node, container.uri)
	# Flat `SymbolInformation`: no nesting, so match by name within the
	# container's own range instead.
	matches = [
		m
		for m in members
		if str(m.get("name") or "") == member_name
		and container.range_start_line <= _member_start_line(m) <= container.range_end_line
	]
	if not matches:
		raise _not_found(query)
	if len(matches) > 1:
		raise _ambiguous(query, matches, workspace_root)
	return _resolved_from_symbol(matches[0])


async def resolve_symbol(
	client: LspClient, workspace_root: Path, query: str, *, file_path: str | None = None
) -> ResolvedSymbol:
	"""Resolve a name (or dotted `Class.method`) to a single symbol position.

	Raises `SymbolResolutionError` (a `ToolInputError`, so tools' existing
	`except TOOL_ERRORS` handles it) when nothing matches or several symbols
	tie on an exact name — callers should pass `file_path` to disambiguate
	rather than guess.
	"""
	if "." in query:
		return await _resolve_dotted(client, workspace_root, query, file_path=file_path)
	return await _resolve_simple(client, workspace_root, query, file_path=file_path)
