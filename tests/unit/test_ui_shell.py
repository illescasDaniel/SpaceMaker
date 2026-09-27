from spacemaker.bootstrap.ui_shell import UI_SHELL_VERSION, stamp_shell_html


def test_given_desktop_shell_html_when_stamp_then_embeds_ui_shell_version() -> None:
	raw = """<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">
	<title>SpaceMaker</title>
</head>
<body>
	<script>window.SPACEMAKER_SHELL = "desktop";</script>
	<script src="/static/app.js"></script>
</body>
</html>
"""
	stamped = stamp_shell_html(raw)
	assert f'content="{UI_SHELL_VERSION}"' in stamped
	assert f'window.SPACEMAKER_UI_SHELL_VERSION = "{UI_SHELL_VERSION}"' in stamped
	assert f'/static/app.js?v={UI_SHELL_VERSION}' in stamped
	assert "EXPECTED_UI_SHELL_VERSION" not in stamped


def test_given_already_stamped_html_when_stamp_again_then_uses_new_version() -> None:
	raw = """<!DOCTYPE html>
<html><head>
	<meta name="ui-shell-version" content="old.version">
</head><body>
	<script>window.SPACEMAKER_SHELL = "desktop"; window.SPACEMAKER_UI_SHELL_VERSION = "old.version";</script>
	<script src="/static/app.js?v=old.version"></script>
</body></html>
"""
	stamped = stamp_shell_html(raw, version="2026.09.next")
	assert stamped.count("2026.09.next") >= 3
	assert "old.version" not in stamped


def test_given_mobile_gallery_shell_when_stamp_then_embeds_version() -> None:
	raw = """<!DOCTYPE html>
<html><head></head><body>
	<script>window.SPACEMAKER_SHELL = "mobile_gallery";</script>
	<script src="/static/app.js"></script>
</body></html>
"""
	stamped = stamp_shell_html(raw)
	assert 'window.SPACEMAKER_SHELL = "mobile_gallery"' in stamped
	assert f'window.SPACEMAKER_UI_SHELL_VERSION = "{UI_SHELL_VERSION}"' in stamped
