from pathlib import Path

from spacemaker.bootstrap.ui_shell import (
	UI_SHELL_VERSION,
	compute_ui_shell_version,
	shell_js_import_map,
	stamp_shell_html,
	webengine_profile_slug,
)


def test_given_desktop_shell_html_when_stamp_then_embeds_ui_shell_version() -> None:
	raw = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>SpaceMaker</title>
	<link rel="stylesheet" href="/static/theme.css">
	<link rel="stylesheet" href="/static/shell-gallery.css">
</head>
<body>
	<script>window.SPACEMAKER_SHELL = "desktop";</script>
	<script type="module" src="/static/js/main.js"></script>
</body>
</html>
"""
	stamped = stamp_shell_html(raw)
	assert f'content="{UI_SHELL_VERSION}"' in stamped
	assert f'window.SPACEMAKER_UI_SHELL_VERSION = "{UI_SHELL_VERSION}"' in stamped
	assert f"/static/js/main.js?v={UI_SHELL_VERSION}" in stamped
	assert f"/static/theme.css?v={UI_SHELL_VERSION}" in stamped
	assert f"/static/shell-gallery.css?v={UI_SHELL_VERSION}" in stamped
	assert 'type="importmap"' in stamped
	assert f'"/static/js/main.js":"/static/js/main.js?v={UI_SHELL_VERSION}"' in stamped
	assert "EXPECTED_UI_SHELL_VERSION" not in stamped


def test_given_already_stamped_html_when_stamp_again_then_uses_new_version() -> None:
	raw = """<!DOCTYPE html>
<html><head>
	<meta name="ui-shell-version" content="old.version">
</head><body>
	<script>window.SPACEMAKER_SHELL = "desktop"; window.SPACEMAKER_UI_SHELL_VERSION = "old.version";</script>
	<script type="importmap">{"imports":{"/static/js/main.js":"/static/js/main.js?v=old.version"}}</script>
	<script type="module" src="/static/js/main.js?v=old.version"></script>
</body></html>
"""
	stamped = stamp_shell_html(raw, version="2026.09.next")
	assert stamped.count("2026.09.next") >= 3
	assert "old.version" not in stamped


def test_given_mobile_gallery_shell_when_stamp_then_embeds_version() -> None:
	raw = """<!DOCTYPE html>
<html><head></head><body>
	<script>window.SPACEMAKER_SHELL = "mobile_gallery";</script>
	<script type="module" src="/static/js/main.js"></script>
</body></html>
"""
	stamped = stamp_shell_html(raw)
	assert 'window.SPACEMAKER_SHELL = "mobile_gallery"' in stamped
	assert f'window.SPACEMAKER_UI_SHELL_VERSION = "{UI_SHELL_VERSION}"' in stamped


def test_given_js_files_when_compute_version_then_changes_with_content(tmp_path: Path) -> None:
	js_dir = tmp_path / "js"
	js_dir.mkdir()
	(js_dir / "a.js").write_text("export const a = 1;\n", encoding="utf-8")
	first = compute_ui_shell_version(js_dir=js_dir)
	(js_dir / "a.js").write_text("export const a = 2;\n", encoding="utf-8")
	second = compute_ui_shell_version(js_dir=js_dir)
	assert first != second
	assert len(first) == 12


def test_given_js_dir_when_import_map_then_maps_each_module(tmp_path: Path) -> None:
	js_dir = tmp_path / "js"
	js_dir.mkdir()
	(js_dir / "api.js").write_text("export {};\n", encoding="utf-8")
	(js_dir / "main.js").write_text("export {};\n", encoding="utf-8")
	payload = shell_js_import_map(version="abc123", js_dir=js_dir)
	assert '"/static/js/api.js":"/static/js/api.js?v=abc123"' in payload
	assert '"/static/js/main.js":"/static/js/main.js?v=abc123"' in payload


def test_given_webengine_profile_when_slug_then_fixed_default() -> None:
	assert webengine_profile_slug() == "default"
