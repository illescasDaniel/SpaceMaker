"""Resolves how to launch `ty server` for codenav's LspClient."""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path


logger = logging.getLogger(__name__)


def resolve_ty_command(workspace_root: Path) -> list[str]:
	venv_bin = "Scripts" if sys.platform == "win32" else "bin"
	venv_exe = "ty.exe" if sys.platform == "win32" else "ty"
	candidate = workspace_root / ".venv" / venv_bin / venv_exe
	if candidate.is_file():
		return [str(candidate), "server"]
	on_path = shutil.which("ty")
	if on_path:
		return [on_path, "server"]
	logger.warning(
		"ty not found in %s/.venv or on PATH; falling back to 'uv run ty server', which installs it on first use.",
		workspace_root,
	)
	return ["uv", "run", "ty", "server"]
