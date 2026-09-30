_Last updated: 2026-09-30 (MCP packages extracted to their own repos)_

## Branch

Primary checkout `main` (ahead of `origin/main`). Worktree `faak` / `cursor/094eb8f7` still on disk.

## Current focus

MCP servers moved out of this repo: `~/Projects/Python/MCPs/{mcp-nav-shared,codenav-mcp,webnav-mcp}`, each its own git repo, public on GitHub under `illescasDaniel/`. SpaceMaker now installs `codenav-mcp`/`webnav-mcp` from PyPI (0.1.0).

## Just changed

- Removed `mcp-servers/` + workspace/`tool.uv.sources`/ty roots/ruff ignores/pytest importlib mode; quality scripts (`checks.py`, `ruff.sh`, `pytest.sh`) no longer touch it. `.mcp.json` unchanged and verified (both servers answer real calls from the PyPI install). `docs/agent-tooling.md` layout + publishing sections rewritten. Gate green.
- The moved repos are at version **0.1.1** (metadata URLs point to the new repos; PyPI's 0.1.0 pages still link to `SpaceMaker/tree/main/mcp-servers/...`, now dead). Each repo has `uploader` group + tasks `upload`/`test-package`.

## Next steps

1. Publish 0.1.1 of all three (shared first) via each repo's `uv run task upload -- --testpypi` → `test-package -- --testpypi` → real index; then bump SpaceMaker's dev pins to `>=0.1.1`.
2. `chmod 600 ~/.pypirc` (currently 644).
3. Restart the codenav/webnav MCPs in the primary session (they now run from the PyPI install); `/delete-worktree` for `faak` when finished.
