_Last updated: 2026-10-05 (webnav-ts-mcp 0.2.0 adopted)_

## Branch

`main`. webnav now starts with `npx --yes webnav-ts-mcp@^0.2.0` in `.mcp.json` and `.cursor/mcp.json` (0.2.0 adds the write tools `edit`, `edit_symbol`, `rename_symbol`, `move`, `quick_fix`, `verify_changes`, `apply_edit`, `undo_edit`, plus a queue so concurrent writes no longer race). codenav still runs from `uvx` (`codenav-mcp>=0.2.0,<0.3`).

## Current focus

Verified 0.2.0 live over `npx` in a Claude Code session: concurrent renames and edits on one file plus parallel reads, then `undo_edit` back to a clean tree. A per-project `webnav` override in `~/.claude.json` (local scope, pointing at the local checkout) had to be removed with `claude mcp remove webnav -s local` so `.mcp.json` takes effect; the first `npx` start downloads about 180 MB.

Next: none pending for this thread. Ideas still open: codenav skipping gitignored paths (e.g. `site/`) in the rename mention scan; jevmem README known limitations.
