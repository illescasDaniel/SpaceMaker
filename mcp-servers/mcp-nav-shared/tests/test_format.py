"""Fast unit tests for `mcp_nav_shared.format` (no live language servers)."""

from __future__ import annotations

from mcp_nav_shared.format import (
	format_callers,
	format_diagnostic,
	format_diagnostics,
	format_location,
	format_outline,
	format_references,
	format_references_grouped,
	format_workspace_symbol,
	format_workspace_symbols,
	is_hierarchical_document_symbols,
	rank_workspace_symbols,
	to_symbol_tree,
	uri_to_relative,
	workspace_symbol_position,
)


def test_given_location_when_format_then_header_includes_line_and_column(tmp_path):
	# given
	src = tmp_path / "pkg" / "mod.py"
	src.parent.mkdir()
	src.write_text("\n\nclass Foo:\n\tpass\n", encoding="utf-8")
	loc = {
		"uri": src.as_uri(),
		"range": {
			"start": {"line": 2, "character": 6},
			"end": {"line": 2, "character": 9},
		},
	}
	# when
	text = format_location(loc, tmp_path)
	# then
	assert text.splitlines()[0] == "pkg/mod.py:3:7"
	assert "class Foo:" in text


def test_given_location_link_when_format_then_prefers_selection_range(tmp_path):
	# given
	src = tmp_path / "a.py"
	src.write_text("x = 1\n", encoding="utf-8")
	loc = {
		"targetUri": src.as_uri(),
		"targetRange": {
			"start": {"line": 0, "character": 0},
			"end": {"line": 0, "character": 5},
		},
		"targetSelectionRange": {
			"start": {"line": 0, "character": 0},
			"end": {"line": 0, "character": 1},
		},
	}
	# when
	header = format_location(loc, tmp_path).splitlines()[0]
	# then
	assert header == "a.py:1:1"


def test_given_uri_under_workspace_when_uri_to_relative_then_uses_forward_slashes(tmp_path):
	# given
	nested = tmp_path / "src" / "pkg" / "x.py"
	nested.parent.mkdir(parents=True)
	nested.write_text("pass\n", encoding="utf-8")
	# when / then
	assert uri_to_relative(nested.as_uri(), tmp_path) == "src/pkg/x.py"


def test_given_class_keyword_range_when_format_workspace_symbol_then_column_on_name(tmp_path):
	# given — ty-style SymbolInformation range starts at `class`
	src = tmp_path / "mod.py"
	src.write_text("class Foo:\n\tpass\n", encoding="utf-8")
	sym = {
		"name": "Foo",
		"kind": 5,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 0, "character": 9},
			},
		},
	}
	# when
	line = format_workspace_symbol(sym, tmp_path)
	uri, row, col = workspace_symbol_position(sym)
	# then
	assert line == "Foo  [Class]  (mod.py:1:7)"
	assert uri == src.as_uri()
	assert (row, col) == (0, 6)


def test_given_selection_range_when_workspace_symbol_position_then_uses_it(tmp_path):
	# given
	src = tmp_path / "a.py"
	src.write_text("class Bar:\n\tpass\n", encoding="utf-8")
	sym = {
		"name": "Bar",
		"kind": 5,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 1, "character": 5},
			},
		},
		"selectionRange": {
			"start": {"line": 0, "character": 6},
			"end": {"line": 0, "character": 9},
		},
	}
	# when
	_uri, row, col = workspace_symbol_position(sym)
	# then
	assert (row, col) == (0, 6)


def test_given_name_missing_from_line_when_workspace_symbol_position_then_range_start(tmp_path):
	# given
	src = tmp_path / "a.py"
	src.write_text("x = 1\n", encoding="utf-8")
	sym = {
		"name": "Missing",
		"kind": 13,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 2},
				"end": {"line": 0, "character": 3},
			},
		},
	}
	# when
	_uri, row, col = workspace_symbol_position(sym)
	# then
	assert (row, col) == (0, 2)


def test_given_decorator_range_when_workspace_symbol_position_then_name_on_next_line(tmp_path):
	# given — ty often starts SymbolInformation on `@dataclass`
	src = tmp_path / "mod.py"
	src.write_text("@dataclass\nclass Foo:\n\tpass\n", encoding="utf-8")
	sym = {
		"name": "Foo",
		"kind": 5,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 0, "character": 10},
			},
		},
	}
	# when
	line = format_workspace_symbol(sym, tmp_path)
	_uri, row, col = workspace_symbol_position(sym)
	# then
	assert line == "Foo  [Class]  (mod.py:2:7)"
	assert (row, col) == (1, 6)


def test_given_stacked_decorators_when_workspace_symbol_position_then_finds_name(tmp_path):
	# given — single-line decorator range + several `@` lines before the def
	src = tmp_path / "mod.py"
	src.write_text(
		"@a\n@b\n@c\n@d\ndef target():\n\tpass\n",
		encoding="utf-8",
	)
	sym = {
		"name": "target",
		"kind": 12,
		"location": {
			"uri": src.as_uri(),
			"range": {
				"start": {"line": 0, "character": 0},
				"end": {"line": 0, "character": 2},
			},
		},
	}
	# when
	_uri, row, col = workspace_symbol_position(sym)
	# then — `def target` is line index 4; name starts after "def "
	assert (row, col) == (4, 4)


def test_given_many_symbols_when_format_workspace_symbols_then_caps_with_note(tmp_path):
	# given
	src = tmp_path / "m.py"
	src.write_text("a = 1\n", encoding="utf-8")
	symbols = [
		{
			"name": f"S{i}",
			"kind": 13,
			"location": {
				"uri": src.as_uri(),
				"range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}},
			},
		}
		for i in range(3)
	]
	# when
	text = format_workspace_symbols(symbols, tmp_path, limit=2)
	# then
	assert text.count("\n") == 2  # two results + truncation line
	assert "S0  [Variable]" in text
	assert "S1  [Variable]" in text
	assert "S2" not in text
	assert "… and 1 more (showing first 2)" in text


def _symbol(name: str, uri: str) -> dict:
	return {
		"name": name,
		"kind": 12,
		"location": {"uri": uri, "range": {"start": {"line": 0, "character": 0}, "end": {"line": 0, "character": 1}}},
	}


def test_given_fuzzy_hits_before_exact_when_rank_then_exact_prefix_substring_order():
	# given — ty returns fuzzy subsequence hits in workspace order
	names = ["test_lsp_client_thing", "get_client", "LspClientFactory", "lspclient", "LspClient", "MyLspClient"]
	symbols = [_symbol(n, "file:///x.py") for n in names]
	# when
	ranked = [sym["name"] for sym in rank_workspace_symbols(symbols, "LspClient")]
	# then
	assert ranked == [
		"LspClient",
		"lspclient",
		"LspClientFactory",
		"MyLspClient",
		"test_lsp_client_thing",
		"get_client",
	]


def test_given_exact_match_past_cap_when_format_workspace_symbols_then_shown_first(tmp_path):
	# given
	src = tmp_path / "m.py"
	src.write_text("a = 1\n", encoding="utf-8")
	symbols = [_symbol(f"get_thing_{i}", src.as_uri()) for i in range(5)] + [_symbol("get", src.as_uri())]
	# when
	text = format_workspace_symbols(symbols, tmp_path, query="get", limit=2)
	# then
	assert text.splitlines()[0].startswith("get  [Function]")


def _diagnostic(line: int, message: str, severity: int = 1) -> dict:
	return {
		"range": {"start": {"line": line, "character": 0}, "end": {"line": line, "character": 1}},
		"severity": severity,
		"message": message,
	}


def test_given_no_items_when_format_diagnostics_then_no_diagnostics_message():
	# given / when
	text = format_diagnostics([])
	# then
	assert text == "No diagnostics."


def test_given_few_items_when_format_diagnostics_then_one_line_per_item_no_truncation():
	# given
	items = [_diagnostic(0, "bad thing", severity=1), _diagnostic(4, "a hint", severity=4)]
	# when
	text = format_diagnostics(items)
	# then
	lines = text.splitlines()
	assert lines == ["1:1 [error] bad thing", "5:1 [hint] a hint"]


def test_given_many_items_when_format_diagnostics_then_caps_with_note():
	# given — mirrors test_given_many_symbols_when_format_workspace_symbols_then_caps_with_note
	items = [_diagnostic(i, f"error {i}") for i in range(5)]
	# when
	text = format_diagnostics(items, limit=2)
	# then
	lines = text.splitlines()
	assert lines == ["1:1 [error] error 0", "2:1 [error] error 1", "… and 3 more (showing first 2)"]


def test_given_multiline_message_when_format_diagnostic_then_continuation_indented():
	# given — ty's "Code is unreachable" carries a second, unprefixed line;
	# without indenting it, it reads as its own diagnostic
	item = _diagnostic(719, "Code is unreachable\nThis may depend on your current environment and settings")
	# when
	text = format_diagnostic(item)
	# then
	assert text.splitlines() == [
		"720:1 [error] Code is unreachable",
		"    This may depend on your current environment and settings",
	]


def test_given_code_when_format_diagnostic_then_appended_to_severity_tag():
	# given
	item = _diagnostic(0, "bad call", severity=2)
	item["code"] = "invalid-argument-type"
	# when
	text = format_diagnostic(item)
	# then
	assert text == "1:1 [warning invalid-argument-type] bad call"


def test_given_no_code_when_format_diagnostic_then_tag_is_severity_only():
	# given — the plain messages already covered above must not grow a
	# trailing space or "None" once `code` is read
	item = _diagnostic(0, "bad thing", severity=1)
	# when
	text = format_diagnostic(item)
	# then
	assert text == "1:1 [error] bad thing"


def test_given_multiline_message_when_format_diagnostics_then_still_one_entry_in_cap_count():
	# given — a multi-line message must count as one item against the cap,
	# not one per physical line
	items = [
		_diagnostic(0, "first\nsecond line"),
		_diagnostic(1, "another"),
	]
	# when
	text = format_diagnostics(items, limit=5)
	# then
	assert text.splitlines() == [
		"1:1 [error] first",
		"    second line",
		"2:1 [error] another",
	]


def _flat_class_and_method() -> list[dict]:
	# given — ty's flat SymbolInformation for a class containing one method
	return [
		{
			"name": "Foo",
			"kind": 5,
			"location": {"range": {"start": {"line": 0, "character": 0}, "end": {"line": 3, "character": 0}}},
		},
		{
			"name": "bar",
			"kind": 6,
			"location": {"range": {"start": {"line": 1, "character": 1}, "end": {"line": 2, "character": 0}}},
		},
	]


def _hierarchical_class_and_method() -> list[dict]:
	# given — the same shape, but as nested DocumentSymbol (hierarchicalDocumentSymbolSupport)
	return [
		{
			"name": "Foo",
			"kind": 5,
			"range": {"start": {"line": 0, "character": 0}, "end": {"line": 3, "character": 0}},
			"children": [
				{
					"name": "bar",
					"kind": 6,
					"range": {"start": {"line": 1, "character": 1}, "end": {"line": 2, "character": 0}},
					"children": [],
				}
			],
		}
	]


def test_given_location_field_when_is_hierarchical_document_symbols_then_false():
	assert is_hierarchical_document_symbols(_flat_class_and_method()) is False


def test_given_range_field_when_is_hierarchical_document_symbols_then_true():
	assert is_hierarchical_document_symbols(_hierarchical_class_and_method()) is True


def test_given_empty_list_when_is_hierarchical_document_symbols_then_false():
	assert is_hierarchical_document_symbols([]) is False


def test_given_flat_symbol_information_when_to_symbol_tree_then_nests_by_containment():
	# when
	tree = to_symbol_tree(_flat_class_and_method())
	# then
	assert len(tree) == 1
	assert tree[0]["name"] == "Foo"
	assert [c["name"] for c in tree[0]["children"]] == ["bar"]


def test_given_hierarchical_document_symbols_when_to_symbol_tree_then_keeps_nesting():
	# when
	tree = to_symbol_tree(_hierarchical_class_and_method())
	# then
	assert tree[0]["name"] == "Foo"
	assert tree[0]["children"][0]["name"] == "bar"


def test_given_no_symbols_when_format_outline_then_message():
	assert format_outline([]) == "No symbols found."


def test_given_hierarchical_symbols_when_format_outline_then_indents_children():
	# when
	text = format_outline(_hierarchical_class_and_method())
	# then
	assert text.splitlines() == [
		"Foo  [Class]  :1-4",
		"  bar  [Method]  :2-3",
	]


def test_given_single_line_symbol_when_format_outline_then_span_omits_range():
	# given — a one-line symbol (start == end) should print `:N`, not `:N-N`
	symbols = [
		{
			"name": "X",
			"kind": 13,
			"location": {"range": {"start": {"line": 4, "character": 0}, "end": {"line": 4, "character": 5}}},
		}
	]
	# when
	text = format_outline(symbols)
	# then
	assert text.splitlines() == ["X  [Variable]  :5"]


def test_given_flat_symbols_when_format_outline_then_nests_and_indents():
	# when
	text = format_outline(_flat_class_and_method())
	# then
	assert text.splitlines() == [
		"Foo  [Class]  :1-4",
		"  bar  [Method]  :2-3",
	]


def test_given_no_calls_when_format_callers_then_message(tmp_path):
	assert format_callers([], tmp_path) == "No callers found."


def test_given_incoming_calls_when_format_callers_then_lists_call_sites(tmp_path):
	# given
	call = {
		"from": {
			"name": "caller_fn",
			"kind": 12,
			"uri": (tmp_path / "a.py").as_uri(),
			"selectionRange": {"start": {"line": 4, "character": 0}},
		},
		"fromRanges": [
			{"start": {"line": 9, "character": 0}},
			{"start": {"line": 12, "character": 0}},
		],
	}
	# when
	text = format_callers([call], tmp_path)
	# then
	assert text == "caller_fn  [Function]  (a.py:5) calls at L10, L13"


def test_given_no_locations_when_format_references_grouped_then_message(tmp_path):
	assert format_references_grouped([], tmp_path) == "No references found."


def test_given_locations_when_format_references_grouped_then_groups_by_file_with_count(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 0, "character": 0}}},
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 5, "character": 0}}},
		{"uri": (tmp_path / "b.py").as_uri(), "range": {"start": {"line": 2, "character": 0}}},
	]
	# when
	text = format_references_grouped(locs, tmp_path)
	# then
	assert text.splitlines() == [
		"3 reference(s) in 2 file(s):",
		"a.py: L1, L6",
		"b.py: L3",
	]


def test_given_more_files_than_limit_when_format_references_grouped_then_notes_omitted(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / f"f{i}.py").as_uri(), "range": {"start": {"line": 0, "character": 0}}} for i in range(3)
	]
	# when
	text = format_references_grouped(locs, tmp_path, file_limit=2)
	lines = text.splitlines()
	# then
	assert lines[0] == "3 reference(s) in 3 file(s):"
	assert lines[-1] == "… and 1 more file(s)"


def test_given_locations_at_or_under_limit_when_format_references_then_full_snippets(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 0, "character": 0}}},
		{"uri": (tmp_path / "b.py").as_uri(), "range": {"start": {"line": 2, "character": 0}}},
	]
	# when
	text = format_references(locs, tmp_path, snippet_limit=2)
	# then
	assert text == "\n\n".join(format_location(loc, tmp_path) for loc in locs)


def test_given_locations_over_limit_when_format_references_then_compact_grouped_with_columns(tmp_path):
	# given
	locs = [
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 0, "character": 4}}},
		{"uri": (tmp_path / "a.py").as_uri(), "range": {"start": {"line": 5, "character": 0}}},
		{"uri": (tmp_path / "b.py").as_uri(), "range": {"start": {"line": 2, "character": 0}}},
	]
	# when
	text = format_references(locs, tmp_path, snippet_limit=2)
	# then
	assert text.splitlines() == [
		"(compact list: 3 > 2 hits)",
		"3 reference(s) in 2 file(s):",
		"a.py: L1:5, L6:1",
		"b.py: L3:1",
	]


def test_given_no_locations_when_format_references_then_message(tmp_path):
	assert format_references([], tmp_path) == "No references found at that position."
