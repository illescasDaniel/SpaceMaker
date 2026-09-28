"""Fast unit tests for `mcp_nav_shared.resolve` (no live language servers)."""

from __future__ import annotations

import asyncio

import pytest
from mcp_nav_shared.resolve import SymbolResolutionError, resolve_symbol


class _FakeResolveClient:
	"""Duck-typed stand-in for LspClient: resolve_symbol only calls
	`workspace_symbol`/`document_symbol`, both trivial to fake for these tests."""

	def __init__(self, workspace_symbols: list[dict], document_symbols: list[dict] | None = None) -> None:
		self._workspace_symbols = workspace_symbols
		self._document_symbols = document_symbols or []

	async def workspace_symbol(self, query: str) -> list[dict]:
		return self._workspace_symbols

	async def document_symbol(self, file_path: str) -> list[dict]:
		return self._document_symbols


def test_given_single_exact_match_when_resolve_symbol_then_resolves_position(tmp_path):
	# given
	uri = (tmp_path / "pkg" / "mod.py").as_uri()
	sym = {
		"name": "target_fn",
		"kind": 12,
		"location": {"uri": uri, "range": {"start": {"line": 3, "character": 0}, "end": {"line": 3, "character": 9}}},
		"selectionRange": {"start": {"line": 3, "character": 4}, "end": {"line": 3, "character": 13}},
	}
	client = _FakeResolveClient([sym])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "target_fn"))
	# then
	assert resolved.name == "target_fn"
	assert resolved.uri == uri
	assert (resolved.line, resolved.column) == (3, 4)


def test_given_no_match_when_resolve_symbol_then_raises(tmp_path):
	# given
	client = _FakeResolveClient([])
	# when / then
	with pytest.raises(SymbolResolutionError, match="No symbol found"):
		asyncio.run(resolve_symbol(client, tmp_path, "missing"))


def test_given_two_exact_matches_when_resolve_symbol_then_ambiguous_lists_candidates(tmp_path):
	# given
	uri_a = (tmp_path / "a.py").as_uri()
	uri_b = (tmp_path / "b.py").as_uri()
	sym_a = {
		"name": "run",
		"kind": 12,
		"location": {"uri": uri_a, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}},
	}
	sym_b = {
		"name": "run",
		"kind": 12,
		"location": {"uri": uri_b, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}},
	}
	client = _FakeResolveClient([sym_a, sym_b])
	# when / then
	with pytest.raises(SymbolResolutionError) as caught:
		asyncio.run(resolve_symbol(client, tmp_path, "run"))
	text = str(caught.value)
	assert "2 symbols match 'run'" in text
	assert "a.py" in text
	assert "b.py" in text


def test_given_file_path_when_two_exact_matches_then_narrows_to_match(tmp_path):
	# given
	uri_a = (tmp_path / "a.py").as_uri()
	uri_b = (tmp_path / "b.py").as_uri()
	range_ = {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 3}}
	sym_a = {"name": "run", "kind": 12, "location": {"uri": uri_a, "range": range_}, "selectionRange": range_}
	sym_b = {"name": "run", "kind": 12, "location": {"uri": uri_b, "range": range_}, "selectionRange": range_}
	client = _FakeResolveClient([sym_a, sym_b])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "run", file_path="b.py"))
	# then
	assert resolved.uri == uri_b


def test_given_case_exact_and_case_insensitive_match_when_resolve_symbol_then_prefers_exact_case(tmp_path):
	# given: `repo_root` (a function) and `REPO_ROOT` (a constant elsewhere)
	# both match case-insensitively; asking for the lowercase name should
	# resolve straight to the case-exact one instead of raising ambiguous.
	uri_exact = (tmp_path / "a.py").as_uri()
	uri_other = (tmp_path / "b.py").as_uri()
	range_ = {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 9}}
	exact = {"name": "repo_root", "kind": 12, "location": {"uri": uri_exact, "range": range_}, "selectionRange": range_}
	other_case = {
		"name": "REPO_ROOT",
		"kind": 13,
		"location": {"uri": uri_other, "range": range_},
		"selectionRange": range_,
	}
	client = _FakeResolveClient([exact, other_case])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "repo_root"))
	# then
	assert resolved.name == "repo_root"
	assert resolved.uri == uri_exact


def test_given_dotted_query_when_hierarchical_members_then_finds_child_node(tmp_path):
	# given
	uri = (tmp_path / "svc.py").as_uri()
	container_sym = {
		"name": "AppServices",
		"kind": 5,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}}},
		"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
	}
	members = [
		{
			"name": "AppServices",
			"kind": 5,
			"range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}},
			"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
			"children": [
				{
					"name": "enter_module",
					"kind": 6,
					"range": {"start": {"line": 5, "character": 1}, "end": {"line": 7, "character": 0}},
					"selectionRange": {"start": {"line": 5, "character": 5}, "end": {"line": 5, "character": 17}},
					"children": [],
				}
			],
		}
	]
	client = _FakeResolveClient([container_sym], members)
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "AppServices.enter_module"))
	# then
	assert resolved.name == "enter_module"
	assert (resolved.line, resolved.column) == (5, 5)


def test_given_dotted_query_when_flat_members_then_matches_within_container_range(tmp_path):
	# given — no hierarchicalDocumentSymbolSupport: fall back to range containment
	uri = (tmp_path / "svc.py").as_uri()
	container_sym = {
		"name": "AppServices",
		"kind": 5,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}}},
		"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
	}
	member_sym = {
		"name": "enter_module",
		"kind": 6,
		"location": {"uri": uri, "range": {"start": {"line": 5, "character": 1}, "end": {"line": 7, "character": 0}}},
		"selectionRange": {"start": {"line": 5, "character": 5}, "end": {"line": 5, "character": 17}},
	}
	client = _FakeResolveClient([container_sym], [container_sym, member_sym])
	# when
	resolved = asyncio.run(resolve_symbol(client, tmp_path, "AppServices.enter_module"))
	# then
	assert resolved.name == "enter_module"
	assert (resolved.line, resolved.column) == (5, 5)


def test_given_dotted_query_when_member_missing_then_raises(tmp_path):
	# given
	uri = (tmp_path / "svc.py").as_uri()
	container_sym = {
		"name": "AppServices",
		"kind": 5,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 20, "character": 0}}},
		"selectionRange": {"start": {"line": 0, "character": 6}, "end": {"line": 0, "character": 17}},
	}
	client = _FakeResolveClient([container_sym], [])
	# when / then
	with pytest.raises(SymbolResolutionError):
		asyncio.run(resolve_symbol(client, tmp_path, "AppServices.missing_method"))
