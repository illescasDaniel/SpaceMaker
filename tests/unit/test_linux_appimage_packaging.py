"""Contract tests for Linux AppImage / AppDir packaging (no full AppImage build)."""

from __future__ import annotations

import os
from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]
_LINUX = _REPO / "packaging" / "linux-appimage"
_BUILD_APPIMAGE = _REPO / "scripts" / "packaging" / "build_appimage.sh"


def test_given_linux_packaging_scripts_when_checking_layout_then_present_and_executable():
	scripts = [
		_LINUX / "build-appdir.sh",
		_LINUX / "prune_pyqt6.sh",
		_LINUX / "smoke_webengine.py",
		_LINUX / "smoke-appimage.sh",
		_BUILD_APPIMAGE,
	]
	for path in scripts:
		assert path.is_file(), f"missing {path}"
		assert os.access(path, os.X_OK), f"not executable: {path}"


def test_given_prune_script_when_reading_then_keeps_webengine_stack():
	text = (_LINUX / "prune_pyqt6.sh").read_text(encoding="utf-8")
	assert "QtWebEngineCore" in text
	assert "QtWebEngineWidgets" in text
	assert "libQt6WebEngineCore.so" in text
	# Must not delete the WebEngine QML tree like srxy's PySide prune.
	assert "QtWebEngine" not in text or '"$QML/QtWebEngine"' not in text


def test_given_build_appimage_script_when_reading_then_uses_pinned_tool_and_zstd():
	text = _BUILD_APPIMAGE.read_text(encoding="utf-8")
	assert "APPIMAGETOOL_VERSION" in text
	assert "1.9.1" in text
	assert "build-appdir.sh" in text
	assert "compression-level" in text
	assert "19" in text
	assert "SHA256SUMS" in text
	assert ".xz" not in text


def test_given_release_workflow_when_reading_then_runs_on_tags_only():
	workflow = _REPO / ".github" / "workflows" / "appimage.yml"
	assert workflow.is_file()
	text = workflow.read_text(encoding="utf-8")
	assert 'tags: ["v*"]' in text
	assert "softprops/action-gh-release" in text
	assert "build-appimage" in text or "build_appimage" in text


def test_given_bundle_env_when_resolving_repo_root_then_uses_share_tree(tmp_path: Path):
	from spacemaker.bootstrap.paths import bundle_resource_root
	from spacemaker.bootstrap.services import repo_root

	share = tmp_path / "usr" / "share" / "spacemaker"
	(share / "packaging").mkdir(parents=True)
	(share / "docs" / "legal").mkdir(parents=True)
	(share / "docs" / "legal" / "PRIVACY.md").write_text("ok", encoding="utf-8")
	(share / "packaging" / "tool-catalog.json").write_text("{}", encoding="utf-8")

	os.environ["SPACEMAKER_BUNDLE_ROOT"] = str(share)
	try:
		assert bundle_resource_root() == share
		assert repo_root() == share
		assert (repo_root() / "docs" / "legal" / "PRIVACY.md").is_file()
	finally:
		os.environ.pop("SPACEMAKER_BUNDLE_ROOT", None)
