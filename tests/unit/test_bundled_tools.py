from pathlib import Path

import pytest

from spacemaker.bootstrap.bundled_tools import BundledTool, resolve_tool_path


def test_given_bundled_file_exists_when_resolve_frozen_then_uses_bundle(tmp_path: Path):
	# given
	root = tmp_path / "tools"
	root.mkdir()
	bundle_file = root / "ffmpeg"
	bundle_file.write_text("stub")
	# when
	path = resolve_tool_path(
		BundledTool.FFMPEG,
		frozen=True,
		dev_mode=False,
		bundle_root_path=root,
		platform_is_windows=False,
		which=lambda _: None,
	)
	# then
	assert path == bundle_file


def test_given_no_bundle_and_frozen_when_resolve_then_raises(tmp_path: Path):
	# given
	root = tmp_path / "tools"
	root.mkdir()
	# when / then
	with pytest.raises(FileNotFoundError, match="release build"):
		resolve_tool_path(
			BundledTool.ADB,
			frozen=True,
			dev_mode=False,
			bundle_root_path=root,
			platform_is_windows=False,
			which=lambda _: None,
		)


def test_given_dev_without_dev_mode_when_no_bundle_then_raises(tmp_path: Path):
	root = tmp_path / "tools"
	root.mkdir()
	with pytest.raises(FileNotFoundError, match="Bundled tool missing"):
		resolve_tool_path(
			BundledTool.MAGICK,
			frozen=False,
			dev_mode=False,
			bundle_root_path=root,
			platform_is_windows=False,
			which=lambda _: "/usr/bin/magick",
		)


def test_given_dev_mode_when_resolve_then_falls_back_to_path(monkeypatch, tmp_path: Path):
	# given
	root = tmp_path / "tools"
	root.mkdir()
	system_bin = tmp_path / "ffmpeg"
	system_bin.write_text("stub")
	# when
	path = resolve_tool_path(
		BundledTool.FFMPEG,
		frozen=False,
		dev_mode=True,
		bundle_root_path=root,
		platform_is_windows=False,
		which=lambda name: str(system_bin) if name == "ffmpeg" else None,
	)
	# then
	assert path == system_bin


def test_given_windows_when_bundled_adb_then_uses_exe_suffix(tmp_path: Path):
	# given
	root = tmp_path / "tools"
	adb = root / "adb.exe"
	adb.parent.mkdir(parents=True)
	adb.write_text("stub")
	# when
	path = resolve_tool_path(
		BundledTool.ADB,
		frozen=True,
		dev_mode=False,
		bundle_root_path=root,
		platform_is_windows=True,
		which=lambda _: None,
	)
	# then
	assert path.name == "adb.exe"
