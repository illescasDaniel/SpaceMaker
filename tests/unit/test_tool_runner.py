from pathlib import Path

import pytest

from spacemaker.adapters.outbound.media.tool_runner import ToolExecutionError, ToolRunner
from spacemaker.bootstrap.bundled_tools import BundledTool


def test_given_nonzero_exit_when_run_then_raises_with_stderr(tmp_path: Path) -> None:
	tools = tmp_path / "tools"
	tools.mkdir()
	binary = tools / "magick"
	binary.write_text("#!/bin/sh\n echo policy blocked 1>&2\n exit 1\n")
	binary.chmod(0o755)
	runner = ToolRunner(bundle_root_path=tools, platform_is_windows=False)
	with pytest.raises(ToolExecutionError, match="policy blocked"):
		runner.run(BundledTool.MAGICK, ["-version"])
