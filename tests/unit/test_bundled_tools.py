from pathlib import Path

import pytest

from spacemaker.bootstrap.bundled_tools import BundledTool, resolve_tool_path


def test_given_managed_file_exists_when_resolve_then_uses_managed(tmp_path: Path):
	# given
	root = tmp_path / "tools"
	root.mkdir()
	bundle_file = root / "ffmpeg"
	bundle_file.write_text("stub")
	bundle_file.chmod(0o755)
	# when
	path = resolve_tool_path(
		BundledTool.FFMPEG,
		bundle_root_path=root,
		platform_is_windows=False,
		which=lambda _: None,
	)
	# then
	assert path == bundle_file


def test_given_no_managed_when_on_path_then_uses_path(tmp_path: Path):
	# given
	root = tmp_path / "tools"
	root.mkdir()
	system_bin = tmp_path / "ffmpeg"
	system_bin.write_text("stub")
	system_bin.chmod(0o755)
	# when
	path = resolve_tool_path(
		BundledTool.FFMPEG,
		bundle_root_path=root,
		platform_is_windows=False,
		which=lambda name: str(system_bin) if name == "ffmpeg" else None,
	)
	# then
	assert path == system_bin


def test_given_no_managed_and_no_path_when_resolve_then_raises(tmp_path: Path):
	root = tmp_path / "tools"
	root.mkdir()
	with pytest.raises(FileNotFoundError, match="Tool not found"):
		resolve_tool_path(
			BundledTool.ADB,
			bundle_root_path=root,
			platform_is_windows=False,
			which=lambda _: None,
			allow_path_fallback=True,
		)


def test_given_managed_preferred_over_path(tmp_path: Path):
	root = tmp_path / "tools"
	root.mkdir()
	managed = root / "ffmpeg"
	managed.write_text("managed")
	managed.chmod(0o755)
	system = tmp_path / "system-ffmpeg"
	system.write_text("system")
	system.chmod(0o755)
	path = resolve_tool_path(
		BundledTool.FFMPEG,
		bundle_root_path=root,
		platform_is_windows=False,
		which=lambda _: str(system),
	)
	assert path == managed


def test_given_windows_when_managed_adb_then_uses_exe_suffix(tmp_path: Path):
	root = tmp_path / "tools"
	adb = root / "adb.exe"
	adb.parent.mkdir(parents=True)
	adb.write_text("stub")
	adb.chmod(0o755)
	path = resolve_tool_path(
		BundledTool.ADB,
		bundle_root_path=root,
		platform_is_windows=True,
		which=lambda _: None,
	)
	assert path.name == "adb.exe"
