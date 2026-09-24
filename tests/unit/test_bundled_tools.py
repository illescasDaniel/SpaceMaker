from pathlib import Path

import pytest

from spacemaker.bootstrap.bundled_tools import (
	BundledTool,
	_windows_magick_from_common_install_dirs,
	resolve_tool_path,
)


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


def test_given_windows_program_files_magick_when_not_on_path_then_resolves(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	root = tmp_path / "tools"
	root.mkdir()
	magick_exe = tmp_path / "magick.exe"
	magick_exe.write_text("stub")
	magick_exe.chmod(0o755)
	monkeypatch.setattr(
		"spacemaker.bootstrap.bundled_tools._windows_magick_from_common_install_dirs",
		lambda **_kwargs: magick_exe,
	)
	path = resolve_tool_path(
		BundledTool.MAGICK,
		bundle_root_path=root,
		platform_is_windows=True,
		which=lambda _: None,
		allow_path_fallback=True,
	)
	assert path == magick_exe


def test_given_windows_magick_dirs_when_newest_first_then_picks_latest_version(tmp_path: Path):
	program_files = tmp_path / "Program Files"
	for name in ("ImageMagick-7.0.0-Q16", "ImageMagick-7.1.2-Q16-HDRI"):
		folder = program_files / name
		folder.mkdir(parents=True)
		exe = folder / "magick.exe"
		exe.write_text(name)
		exe.chmod(0o755)
	chosen = _windows_magick_from_common_install_dirs(roots=(program_files,))
	assert chosen is not None
	assert chosen.parent.name == "ImageMagick-7.1.2-Q16-HDRI"
