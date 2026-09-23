from pathlib import Path

import pytest

from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError, ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool


def test_given_nonzero_exit_when_run_then_raises_with_stderr(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	tools = tmp_path / "tools"
	tools.mkdir()
	binary = tools / "magick"
	binary.write_text("#!/bin/sh\n echo policy blocked 1>&2\n exit 1\n")
	binary.chmod(0o755)
	monkeypatch.setenv("PATH", "")
	runner = ToolRunner(
		bundle_root_path=tools,
		platform_is_windows=False,
		path_fallback_allowed=lambda _tool: False,
	)
	with pytest.raises(ToolExecutionError, match="policy blocked"):
		runner.run(BundledTool.MAGICK, ["-version"])


def test_given_managed_ffmpeg_without_hw_when_path_allowed_then_prefers_system_ffmpeg(
	tmp_path: Path,
	monkeypatch: pytest.MonkeyPatch,
) -> None:
	tools = tmp_path / "tools"
	tools.mkdir()
	system_bin = tmp_path / "system-bin"
	system_bin.mkdir()
	managed = tools / "ffmpeg"
	system = system_bin / "ffmpeg"
	managed.write_text("#!/bin/sh\necho 'encoders:'\necho ' libx264'\n")
	system.write_text("#!/bin/sh\necho 'encoders:'\necho ' h264_nvenc'\n")
	managed.chmod(0o755)
	system.chmod(0o755)
	monkeypatch.setenv("PATH", str(system_bin))
	runner = ToolRunner(
		bundle_root_path=tools,
		platform_is_windows=False,
		path_fallback_allowed=lambda _tool: True,
	)
	assert runner.path(BundledTool.FFMPEG).resolve() == system.resolve()
