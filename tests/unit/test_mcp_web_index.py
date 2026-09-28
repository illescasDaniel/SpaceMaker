"""Fast unit tests for webnav's workspace-wide CSS var / selector index (no live language servers)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_MCP_ROOT = Path(__file__).resolve().parents[2] / "mcp-servers"
if str(_MCP_ROOT) not in sys.path:
	sys.path.insert(0, str(_MCP_ROOT))

from webnav_mcp import web_index  # noqa: E402


def _write(path: Path, text: str) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(text, encoding="utf-8")
	return path


def test_given_nested_media_query_declarations_when_scan_then_context_breadcrumb_built(tmp_path):
	# given
	css = _write(
		tmp_path / "theme.css",
		":root {\n\t--bg: #fff;\n}\n@media (prefers-color-scheme: dark) {\n\t:root {\n\t\t--bg: #000;\n\t}\n}\n",
	)
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	decls = idx.var_declarations["--bg"]
	assert [d.context for d in decls] == [":root", "@media (prefers-color-scheme: dark) › :root"]
	assert [d.value for d in decls] == ["#fff", "#000"]
	assert all(d.file == css.name for d in decls)


def test_given_var_usage_with_and_without_fallback_when_scan_then_has_fallback_flag_correct(tmp_path):
	# given
	_write(tmp_path / "a.css", ".x { color: var(--bg); border-color: var(--bg, red); }\n")
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	usages = idx.var_usages["--bg"]
	assert [u.has_fallback for u in usages] == [False, True]


def test_given_declaration_inside_css_comment_when_scan_then_ignored(tmp_path):
	# given
	_write(tmp_path / "a.css", "/* --bg: #fff; */\n:root {\n\t--bg: #000;\n}\n")
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	decls = idx.var_declarations["--bg"]
	assert len(decls) == 1
	assert decls[0].value == "#000"


def test_given_html_style_block_and_style_attr_when_scan_then_var_decl_and_usage_found(tmp_path):
	# given
	_write(
		tmp_path / "index.html",
		'<html>\n<style>\n\t:root {\n\t\t--bg: #fff;\n\t}\n</style>\n<body>\n<div style="color: var(--bg);"></div>\n</body>\n</html>\n',
	)
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.var_declarations["--bg"][0].value == "#fff"
	assert idx.var_usages["--bg"][0].file == "index.html"


def test_given_js_setproperty_and_getpropertyvalue_when_scan_then_usage_recorded(tmp_path):
	# given
	_write(
		tmp_path / "app.js",
		'root.style.setProperty("--bg", "#000");\nconst v = root.style.getPropertyValue("--bg");\n',
	)
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	usages = idx.var_usages["--bg"]
	assert len(usages) == 2
	assert usages[0].line == 1
	assert usages[1].line == 2


def test_given_two_roots_when_build_workspace_index_then_kept_separate(tmp_path):
	# given
	_write(tmp_path / web_index.STATIC_ROOT_REL / "theme.css", ":root {\n\t--bg: #fff;\n}\n")
	_write(tmp_path / web_index.WIREFRAME_ROOT_REL / "app.html", "<style>\n:root {\n\t--bg: #eee;\n}\n</style>\n")
	# when
	indexes = web_index.build_workspace_index(tmp_path)
	# then
	static_idx = next(i for i in indexes if i.name == "static")
	wireframe_idx = next(i for i in indexes if i.name == "wireframes")
	assert static_idx.var_declarations["--bg"][0].value == "#fff"
	assert wireframe_idx.var_declarations["--bg"][0].value == "#eee"


def test_given_var_declared_and_used_when_format_css_var_then_grouped_by_root(tmp_path):
	# given
	_write(tmp_path / web_index.STATIC_ROOT_REL / "theme.css", ":root {\n\t--bg: #fff;\n}\n")
	_write(tmp_path / web_index.STATIC_ROOT_REL / "shell.css", ".x { background: var(--bg); }\n")
	indexes = web_index.build_workspace_index(tmp_path)
	# when
	text = web_index.format_css_var(indexes, "bg")
	# then
	assert "--bg" in text
	assert "== static ==" in text
	assert "theme.css:2" in text
	assert "shell.css: L1" in text


def test_given_var_never_defined_or_used_when_format_css_var_then_says_not_found(tmp_path):
	# given
	indexes = web_index.build_workspace_index(tmp_path)
	# when
	text = web_index.format_css_var(indexes, "--nope")
	# then
	assert "not defined or used" in text


def test_given_var_without_fallback_and_no_declaration_when_diagnostics_for_file_then_warns(tmp_path):
	# given
	_write(tmp_path / "a.css", ".x { color: var(--missing); }\n")
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	warnings = web_index.diagnostics_for_file(idx, "a.css")
	# then
	assert any("var(--missing) is never defined" in w for w in warnings)


def test_given_var_with_fallback_and_no_declaration_when_diagnostics_for_file_then_no_warning(tmp_path):
	# given
	_write(tmp_path / "a.css", ":root { color: var(--missing, red); }\n")
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	warnings = web_index.diagnostics_for_file(idx, "a.css")
	# then
	assert warnings == []


def test_given_column_on_var_token_when_token_at_position_then_returns_var_name():
	# given
	line = "\tbackground: var(--bg);"
	col = line.index("--bg") + 2  # inside "--bg", 1-indexed
	# when
	found = web_index.token_at_position(line, col)
	# then
	assert found == "--bg"


def test_given_column_on_class_selector_when_token_at_position_then_returns_class():
	# given
	line = ".gallery-item-thumb { display: block; }"
	col = 3  # inside ".gallery-item-thumb"
	# when
	found = web_index.token_at_position(line, col)
	# then
	assert found == ".gallery-item-thumb"


def test_given_column_outside_any_token_when_token_at_position_then_none():
	# given
	line = "body { margin: 0; }"
	# when
	found = web_index.token_at_position(line, 1)
	# then
	assert found is None


def test_given_id_and_class_attrs_in_html_when_scan_then_selector_hits_recorded(tmp_path):
	# given
	_write(tmp_path / "index.html", '<div id="view-gallery" class="screen active"></div>\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits["#view-gallery"][0].kind == "html"
	assert {h.token for h in idx.selector_hits.get(".screen", [])} == {".screen"}
	assert {h.token for h in idx.selector_hits.get(".active", [])} == {".active"}


def test_given_classlist_add_multiple_tokens_when_scan_js_then_each_token_recorded(tmp_path):
	# given
	_write(tmp_path / "app.js", 'el.classList.add("thumb-removing", "is-selected");\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits[".thumb-removing"][0].detail == "classList.add"
	assert idx.selector_hits[".is-selected"][0].detail == "classList.add"


def test_given_query_selector_all_when_scan_js_then_compound_selector_tokens_recorded(tmp_path):
	# given
	_write(tmp_path / "app.js", 'document.querySelectorAll(".screen.active");\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits[".screen"][0].detail == "querySelector"
	assert idx.selector_hits[".active"][0].detail == "querySelector"


def test_given_classname_assignment_when_scan_js_then_tokens_recorded(tmp_path):
	# given
	_write(tmp_path / "app.js", 'el.className = "gallery-item-thumb selected";\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits[".gallery-item-thumb"][0].detail == "className"
	assert idx.selector_hits[".selected"][0].detail == "className"


def test_given_dynamic_get_element_by_id_concat_when_scan_js_then_tagged_dynamic_partial(tmp_path):
	# given
	_write(tmp_path / "app.js", 'document.getElementById("view-" + resolved);\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits["#view-"][0]
	assert hit.dynamic is True
	assert hit.kind == "js"


def test_given_static_get_element_by_id_when_scan_js_then_not_tagged_dynamic(tmp_path):
	# given
	_write(tmp_path / "app.js", 'document.getElementById("view-gallery");\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits["#view-gallery"][0]
	assert hit.dynamic is False


def test_given_css_rule_with_no_html_js_reference_when_diagnostics_for_file_then_warns(tmp_path):
	# given
	_write(tmp_path / "a.css", ".orphan-class { color: red; }\n")
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	warnings = web_index.diagnostics_for_file(idx, "a.css")
	# then
	assert any(".orphan-class is never referenced" in w for w in warnings)


def test_given_css_rule_referenced_in_html_when_diagnostics_for_file_then_no_warning(tmp_path):
	# given
	_write(tmp_path / "a.css", ".used-class { color: red; }\n")
	_write(tmp_path / "index.html", '<div class="used-class"></div>\n')
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	warnings = web_index.diagnostics_for_file(idx, "a.css")
	# then
	assert warnings == []


def test_given_only_dynamic_js_hit_when_unreferenced_selectors_then_still_flagged(tmp_path):
	# given
	_write(tmp_path / "a.css", "#view-gallery { display: block; }\n")
	_write(tmp_path / "app.js", 'document.getElementById("view-" + name);\n')
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	unreferenced = web_index.unreferenced_selectors(idx)
	# then
	assert "#view-gallery" in unreferenced


@pytest.mark.parametrize("token", ["#foo", ".foo"])
def test_given_valid_selector_token_when_token_kind_then_matches_prefix(token):
	# when / then
	assert web_index.token_kind(token) == ("id" if token.startswith("#") else "class")


def test_given_non_selector_string_when_token_kind_then_none():
	# when / then
	assert web_index.token_kind("--bg") is None
