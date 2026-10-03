_Last updated: 2026-10-04 (codenav 0.2.0 from PyPI verified)_

## Branch

`worktree-codenav-local-write-tools-trial`. The codenav write tools (`edit`, `edit_symbol`, `rename_symbol`, `change_signature`, `move`, `quick_fix`, `verify_changes`, `apply_edit`, `undo_edit`) are now published as `codenav-mcp` 0.2.0 / `mcp-nav-shared` 0.2.0. `.mcp.json` runs codenav from the published dependency again (`uv run --directory`), `pyproject.toml` requires `codenav-mcp>=0.2.0`, `uv.lock` updated.

## Current focus

Trial finished: the published 0.2.0 server was driven over stdio from this repo (19 tools, create/edit-refused/rename/verify all fine); the trial log was deleted (findings live in the MCP repos). A running Claude/Cursor session needs an MCP restart to pick up 0.2.0.

Next: land the branch on `main`; then the jevmem README known limitations (per-branch scope, instructions-file filter misses); untried codenav options (`include_overrides`, parameter rename, whole-module `move`).
