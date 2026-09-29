"""Fast unit tests for webnav's workspace-wide CSS var / selector index (no live language servers)."""

from __future__ import annotations

from pathlib import Path

import pytest
from webnav_mcp import web_index


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


def test_given_no_roots_arg_when_build_workspace_index_then_single_default_root_over_whole_tree(tmp_path):
	# given
	_write(tmp_path / "theme.css", ":root {\n\t--bg: #fff;\n}\n")
	# when
	indexes = web_index.build_workspace_index(tmp_path)
	# then
	assert [i.name for i in indexes] == [web_index.DEFAULT_ROOT_LABEL]
	assert indexes[0].var_declarations["--bg"][0].value == "#fff"


def test_given_explicit_roots_list_when_build_workspace_index_then_kept_separate(tmp_path):
	# given
	_write(tmp_path / "static" / "theme.css", ":root {\n\t--bg: #fff;\n}\n")
	_write(tmp_path / "wireframes" / "app.html", "<style>\n:root {\n\t--bg: #eee;\n}\n</style>\n")
	roots = [("static", tmp_path / "static"), ("wireframes", tmp_path / "wireframes")]
	# when
	indexes = web_index.build_workspace_index(tmp_path, roots)
	# then
	static_idx = next(i for i in indexes if i.name == "static")
	wireframe_idx = next(i for i in indexes if i.name == "wireframes")
	assert static_idx.var_declarations["--bg"][0].value == "#fff"
	assert wireframe_idx.var_declarations["--bg"][0].value == "#eee"


def test_given_named_subdir_root_when_build_workspace_index_then_file_paths_are_workspace_relative(tmp_path):
	# given — a named root that's a subdirectory of the workspace; reported
	# `file` paths should be relative to the *workspace*, consistent with
	# every other webnav tool, not relative to the named root itself (which
	# would silently drop the "static/" prefix and look wrong/ambiguous).
	_write(tmp_path / "static" / "theme.css", ":root {\n\t--bg: #fff;\n}\n")
	roots = [("static", tmp_path / "static")]
	# when
	indexes = web_index.build_workspace_index(tmp_path, roots)
	# then
	decl = indexes[0].var_declarations["--bg"][0]
	assert decl.file == "static/theme.css"


def test_given_roots_env_string_when_parse_roots_env_then_labels_map_to_absolute_paths(tmp_path):
	# given
	raw = "static=src/static,wireframes=wireframes"
	# when
	roots = web_index.parse_roots_env(raw, tmp_path)
	# then
	assert roots == [
		("static", (tmp_path / "src" / "static").resolve()),
		("wireframes", (tmp_path / "wireframes").resolve()),
	]


def test_given_entry_without_equals_when_parse_roots_env_then_raises(tmp_path):
	# given / when / then
	with pytest.raises(ValueError, match="label=relative/path"):
		web_index.parse_roots_env("static", tmp_path)


def test_given_var_declared_and_used_when_format_css_var_then_grouped_by_root(tmp_path):
	# given
	_write(tmp_path / "static" / "theme.css", ":root {\n\t--bg: #fff;\n}\n")
	_write(tmp_path / "static" / "shell.css", ".x { background: var(--bg); }\n")
	indexes = web_index.build_workspace_index(tmp_path, [("static", tmp_path / "static")])
	# when
	text = web_index.format_css_var(indexes, "bg")
	# then
	assert "--bg" in text
	assert "== static ==" in text
	assert "theme.css:2" in text
	assert "shell.css: L1" in text


def test_given_var_never_defined_or_used_when_format_css_var_then_says_not_found(tmp_path):
	# given
	indexes = web_index.build_workspace_index(tmp_path, [("static", tmp_path / "static")])
	# when
	text = web_index.format_css_var(indexes, "--nope")
	# then
	assert "not defined or used" in text
	assert "static" in text


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


def test_given_classname_assign_inside_inline_script_when_scan_html_then_recorded_with_correct_line(tmp_path):
	# given: inline <script> was previously not scanned at all, so a
	# selector referenced only from a wireframe's own inline JS looked unused.
	_write(
		tmp_path / "index.html",
		"<html>\n<body>\n<script>\n\trow.className = 'file-row';\n</script>\n</body>\n</html>\n",
	)
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits[".file-row"][0]
	assert hit.kind == "js"
	assert hit.detail == "className"
	assert hit.line == 4


def test_given_orphan_css_rule_referenced_only_from_inline_script_when_diagnostics_then_no_warning(tmp_path):
	# given
	_write(
		tmp_path / "index.html",
		"<style>.file-row { color: red; }</style>\n<script>\nrow.className = 'file-row';\n</script>\n",
	)
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	warnings = web_index.diagnostics_for_file(idx, "index.html")
	# then
	assert warnings == []


def test_given_script_tag_with_src_attribute_when_scan_html_then_body_not_double_scanned(tmp_path):
	# given: an external script has no inline body between the tags; this
	# just documents that the empty capture is harmless, not a crash.
	_write(tmp_path / "index.html", '<script src="app.js"></script>\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits == {}


def test_given_class_variable_built_with_plus_equals_when_scan_js_then_tokens_recorded(tmp_path):
	# given: a local variable conventionally named like a class list
	# (`mediaClass`), grown with `+=`, rather than a direct `.className` write.
	_write(tmp_path / "app.js", "var mediaClass = 'gallery-item-media';\nmediaClass += ' slide-in-next-start';\n")
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits[".slide-in-next-start"][0]
	assert hit.kind == "js"
	assert hit.detail == "class-var +="
	assert hit.dynamic is False


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


def test_given_only_dynamic_js_hit_when_unreferenced_selectors_then_not_flagged(tmp_path):
	# given: a dynamic prefix hit (`#view-`) is a plausible reference to any
	# id it's a prefix of, so it suppresses the "never referenced" warning.
	_write(tmp_path / "a.css", "#view-gallery { display: block; }\n")
	_write(tmp_path / "app.js", 'document.getElementById("view-" + name);\n')
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	unreferenced = web_index.unreferenced_selectors(idx)
	# then
	assert "#view-gallery" not in unreferenced


def test_given_class_attr_inside_js_string_literal_when_scan_js_then_recorded(tmp_path):
	# given
	_write(tmp_path / "app.js", "el.innerHTML = '<span class=\"gallery-loading-spinner\">x</span>';\n")
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits[".gallery-loading-spinner"][0]
	assert hit.kind == "js"
	assert hit.detail == "class attribute in JS string"


def test_given_id_attr_inside_js_string_literal_when_scan_js_then_recorded(tmp_path):
	# given
	_write(tmp_path / "app.js", "el.innerHTML = \"<div id='gallery-root'></div>\";\n")
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits["#gallery-root"][0]
	assert hit.kind == "js"
	assert hit.detail == "id attribute in JS string"


def test_given_classname_assign_with_concatenation_when_scan_js_then_last_token_dynamic(tmp_path):
	# given
	_write(tmp_path / "app.js", 'el.className = "tool-status resolution-" + kind;\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits[".tool-status"][0].dynamic is False
	assert idx.selector_hits[".resolution-"][0].dynamic is True


def test_given_classlist_add_with_concatenation_when_scan_js_then_tagged_dynamic(tmp_path):
	# given
	_write(tmp_path / "app.js", 'el.classList.add("is-" + state);\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	hit = idx.selector_hits[".is-"][0]
	assert hit.dynamic is True
	assert hit.detail == "classList.add"


def test_given_trailing_space_before_concatenation_when_scan_js_then_not_dynamic(tmp_path):
	# given: a trailing space means the concatenation starts a fresh class
	# name, not a suffix of "tool-status".
	_write(tmp_path / "app.js", 'el.className = "tool-status " + extra;\n')
	# when
	idx = web_index.build_root_index(tmp_path, "static")
	# then
	assert idx.selector_hits[".tool-status"][0].dynamic is False


def test_given_dynamic_prefix_hit_when_format_selector_then_surfaced_as_partial_match(tmp_path):
	# given
	_write(tmp_path / "app.js", 'document.getElementById("view-" + resolved);\n')
	idx = web_index.build_root_index(tmp_path, "static")
	# when
	text = web_index.format_selector([idx], "#view-gallery")
	# then
	assert "dynamic partial match via '#view-'" in text


@pytest.mark.parametrize("token", ["#foo", ".foo"])
def test_given_valid_selector_token_when_token_kind_then_matches_prefix(token):
	# when / then
	assert web_index.token_kind(token) == ("id" if token.startswith("#") else "class")


def test_given_non_selector_string_when_token_kind_then_none():
	# when / then
	assert web_index.token_kind("--bg") is None


def test_given_ts_source_when_scan_then_var_usage_recorded(tmp_path):
	# given
	_write(
		tmp_path / "theme.ts",
		'el.style.setProperty("--accent", "red");\nconst x: string = el.style.getPropertyValue("--accent");\n',
	)
	# when
	idx = web_index.build_root_index(tmp_path, "web")
	# then
	assert "--accent" in idx.var_usages


def test_given_unchanged_files_when_build_root_index_twice_then_reuses_index(tmp_path):
	# given
	_write(tmp_path / "a.css", ":root { --a: 1; }\n")
	# when
	first = web_index.build_root_index(tmp_path, "static")
	second = web_index.build_root_index(tmp_path, "static")
	# then
	assert first is second


@pytest.mark.parametrize("mutate", ["edit", "add", "delete"])
def test_given_changed_files_when_build_root_index_then_cache_invalidated(tmp_path, mutate):
	# given
	css = _write(tmp_path / "a.css", ":root { --a: 1; }\n")
	first = web_index.build_root_index(tmp_path, "static")
	# when
	if mutate == "edit":
		css.write_text(":root { --a: 1; --bb: 2; }\n", encoding="utf-8")
	elif mutate == "add":
		_write(tmp_path / "b.css", ":root { --b: 2; }\n")
	else:
		css.unlink()
	second = web_index.build_root_index(tmp_path, "static")
	# then
	assert second is not first
