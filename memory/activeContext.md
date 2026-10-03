_Last updated: 2026-10-04 (codenav write tools verified)_

## Branch

`worktree-codenav-local-write-tools-trial`. Trial of the codenav write tools (`edit`, `edit_symbol`, `rename_symbol`, `change_signature`, `move`, `quick_fix`, `verify_changes`, `apply_edit`, `undo_edit`) from the local checkouts `~/Projects/Code/MCPs/{codenav-mcp,mcp-nav-shared}` (branch `claude/write-tools`), wired in `.mcp.json` with `--no-project --with-editable` (absolute local paths; revert with `git checkout 10b9af4 -- .mcp.json` when the trial ends). jevmem still runs from PyPI (see `memory/README.md`).

## Current focus

Trial log in `memory/mcp-write-tools-trial.md` (Round 3 = verification of the 9-tool surface: everything worked, including previews, `apply_edit`, stale-preview refusal and undo). The write-tools changes in the two MCP repos are committed and pushed on `claude/write-tools`.

Next: publish `mcp-nav-shared` 0.2.0 and `codenav-mcp` so SpaceMaker can depend on them again; exercise the untried options (`include_overrides`, parameter rename, whole-module `move`); then delete the trial log and revert `.mcp.json`. Earlier jevmem wrap-up (land on `main`, README known limitations) still stands.
