"""Contract tests for macOS DMG / SpaceMaker.app packaging (no full PyInstaller build)."""

from __future__ import annotations

import os
from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]
_BUILD_DMG = _REPO / "scripts" / "packaging" / "build_macos_dmg.sh"
_SPEC = _REPO / "packaging" / "spacemaker.spec"
_SYNC_ICONS = _REPO / "scripts" / "packaging" / "sync_brand_icons.py"


def test_given_macos_packaging_scripts_when_checking_layout_then_present_and_executable():
	for path in (_BUILD_DMG, _SYNC_ICONS):
		assert path.is_file(), f"missing {path}"
		assert os.access(path, os.X_OK), f"not executable: {path}"
	assert _SPEC.is_file()


def test_given_build_macos_dmg_script_when_reading_then_uses_hdiutil_and_icns():
	text = _BUILD_DMG.read_text(encoding="utf-8")
	assert "hdiutil" in text
	assert "spacemaker.icns" in text
	assert "codesign" in text
	assert "SHA256SUMS" in text
	assert "SpaceMaker.app" in text
	assert "Contents/MacOS/SpaceMaker" in text


def test_given_pyinstaller_spec_when_reading_then_bundles_macos_app():
	text = _SPEC.read_text(encoding="utf-8")
	assert "BUNDLE" in text
	assert "SpaceMaker.app" in text
	assert "eu.daniel-ir.spacemaker" in text
	assert "exclude_binaries=True" in text
	assert "spacemaker.icns" in text


def test_given_icon_sync_when_reading_then_writes_icns_on_darwin():
	text = _SYNC_ICONS.read_text(encoding="utf-8")
	assert "iconutil" in text
	assert "spacemaker.icns" in text
	assert "darwin" in text
