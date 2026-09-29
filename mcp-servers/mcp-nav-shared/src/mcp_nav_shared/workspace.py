"""Resolve the workspace root for project MCP servers.

Hosts may spawn stdio MCP processes with a cwd that is not the repo
(e.g. Cursor using $HOME). Prefer an explicit override, then Claude Code's
injected project dir, then the process's current working directory — never
a path baked into this package's own install location, since that would
silently point every un-configured host at wherever these servers happen to
be installed from (e.g. this repo) instead of the project actually being
worked on.
"""

from __future__ import annotations

import os
from pathlib import Path


def resolve_workspace_root(explicit_env: str) -> Path:
	for key in (explicit_env, "CLAUDE_PROJECT_DIR"):
		raw = os.environ.get(key)
		if raw:
			return Path(raw).expanduser().resolve()
	return Path.cwd().resolve()


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
