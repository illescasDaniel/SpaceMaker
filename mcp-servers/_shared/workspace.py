"""Resolve the workspace root for project MCP servers.

Hosts may spawn stdio MCP processes with a cwd that is not the repo
(e.g. Cursor using $HOME). Prefer an explicit override, then Claude Code's
injected project dir, then the repo root inferred from this package path.
"""

from __future__ import annotations

import os
from pathlib import Path


# mcp-servers/_shared/workspace.py → repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def resolve_workspace_root(explicit_env: str) -> Path:
	for key in (explicit_env, "CLAUDE_PROJECT_DIR"):
		raw = os.environ.get(key)
		if raw:
			return Path(raw).expanduser().resolve()
	return _REPO_ROOT


def resolve_source_root(explicit_env: str, workspace_root: Path) -> Path:
	"""Root directory for import-path derivation and workspace-wide class
	scanning (codenav's `implementations`). Not every project keeps its
	source under `src/`, so default to the workspace root itself (scan
	everything) rather than assuming a layout; a project that wants a
	narrower/faster scan sets `explicit_env` (e.g. to `src`) in its MCP
	server config."""
	raw = os.environ.get(explicit_env)
	if raw:
		path = Path(raw)
		return path if path.is_absolute() else (workspace_root / path).resolve()
	return workspace_root
