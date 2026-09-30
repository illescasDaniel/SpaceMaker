from pathlib import Path

import pytest

from spacemaker.bootstrap.bundled_tools import (
	BundledTool,
	_tool_from_host_path_dirs,
	_windows_magick_from_common_install_dirs,
	components_tools,
	ensure_host_tool_path_dirs,
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


def test_given_host_bin_dir_missing_from_path_when_ensure_then_prepends(tmp_path: Path) -> None:
	# given
	brew_bin = tmp_path / "opt" / "homebrew" / "bin"
	brew_bin.mkdir(parents=True)
	env = {"PATH": "/usr/bin:/bin"}
	# when
	added = ensure_host_tool_path_dirs(environ=env, extra_dirs=(brew_bin,))
	# then
	assert added == [str(brew_bin)]
	assert env["PATH"].startswith(f"{brew_bin}:")


def test_given_host_bin_already_on_path_when_ensure_then_no_duplicate(tmp_path: Path) -> None:
	# given
	brew_bin = tmp_path / "opt" / "homebrew" / "bin"
	brew_bin.mkdir(parents=True)
	env = {"PATH": f"{brew_bin}:/usr/bin"}
	# when
	added = ensure_host_tool_path_dirs(environ=env, extra_dirs=(brew_bin,))
	# then
	assert added == []
	assert env["PATH"] == f"{brew_bin}:/usr/bin"


def test_given_brew_style_bin_when_which_misses_then_resolve_uses_host_dir(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	# given
	root = tmp_path / "tools"
	root.mkdir()
	brew_bin = tmp_path / "homebrew" / "bin"
	brew_bin.mkdir(parents=True)
	ffmpeg = brew_bin / "ffmpeg"
	ffmpeg.write_text("stub")
	ffmpeg.chmod(0o755)
	monkeypatch.setattr(
		"spacemaker.bootstrap.bundled_tools.host_tool_path_dirs",
		lambda: [brew_bin],
	)
	# when
	path = resolve_tool_path(
		BundledTool.FFMPEG,
		bundle_root_path=root,
		platform_is_windows=False,
		which=lambda _: None,
		allow_path_fallback=True,
	)
	# then
	assert path == ffmpeg


def test_given_host_bin_when_probe_then_returns_executable(tmp_path: Path) -> None:
	# given
	brew_bin = tmp_path / "bin"
	brew_bin.mkdir()
	magick = brew_bin / "magick"
	magick.write_text("stub")
	magick.chmod(0o755)
	# when
	found = _tool_from_host_path_dirs(
		BundledTool.MAGICK,
		platform_is_windows=False,
		dirs=(brew_bin,),
	)
	# then
	assert found == magick


def test_given_macos_when_components_tools_then_omits_afc():
	# given
	platform = "darwin"
	# when
	tools = components_tools(platform=platform)
	# then
	ids = {tool.value for tool in tools}
	assert "ifuse" not in ids
	assert "idevice_id" not in ids
	assert "ffmpeg" in ids
	assert "adb" in ids


def test_given_windows_when_components_tools_then_omits_afc():
	# given
	platform = "win32"
	# when
	tools = components_tools(platform=platform)
	# then
	ids = {tool.value for tool in tools}
	assert "ifuse" not in ids
	assert "idevicepair" not in ids


def test_given_linux_when_components_tools_then_includes_afc():
	# given
	platform = "linux"
	# when
	tools = components_tools(platform=platform)
	# then
	ids = {tool.value for tool in tools}
	assert ids == {tool.value for tool in BundledTool}
	assert "ifuse" in ids
	assert "ideviceinfo" in ids
