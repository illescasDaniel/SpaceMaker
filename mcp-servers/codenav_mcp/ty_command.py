"""Resolves how to launch `ty server` for codenav's LspClient."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def resolve_ty_command(workspace_root: Path) -> list[str]:
	venv_bin = "Scripts" if sys.platform == "win32" else "bin"
	venv_exe = "ty.exe" if sys.platform == "win32" else "ty"
	candidate = workspace_root / ".venv" / venv_bin / venv_exe
	if candidate.is_file():
		return [str(candidate), "server"]
	on_path = shutil.which("ty")
	if on_path:
		return [on_path, "server"]
	return ["uv", "run", "ty", "server"]
