_Last updated: 2026-10-05 (jevmem 0.3.0 adopted)_

## Branch

`main`. webnav now starts with `npx --yes webnav-ts-mcp@^0.2.0` in `.mcp.json` and `.cursor/mcp.json` (0.2.0 adds the write tools `edit`, `edit_symbol`, `rename_symbol`, `move`, `quick_fix`, `verify_changes`, `apply_edit`, `undo_edit`, plus a queue so concurrent writes no longer race). codenav still runs from `uvx` (`codenav-mcp>=0.2.0,<0.3`).

## Current focus

jevmem 0.3.0 (local and third-party decision models) was tested from the local checkout against hosted Jev and ollaya `jevk5:4b`, released to PyPI, and pinned as `jevmem>=0.3.0,<0.4` in `.mcp.json` and `.cursor/mcp.json`. Re-tested over MCP on the real DB (stats, recall, list) after the restart. ollaya was stopped afterwards. jev-mem repo: README PyPI badge added, GitHub releases v0.3.0 and v0.2.0 created.

Verified 0.2.0 live over `npx` in a Claude Code session: concurrent renames and edits on one file plus parallel reads, then `undo_edit` back to a clean tree. A per-project `webnav` override in `~/.claude.json` (local scope, pointing at the local checkout) had to be removed with `claude mcp remove webnav -s local` so `.mcp.json` takes effect; the first `npx` start downloads about 180 MB.

Next: none pending for this thread (jevmem local-model MCP path is only CLI-verified on the published package). Ideas still open: codenav skipping gitignored paths (e.g. `site/`) in the rename mention scan; jevmem README known limitations.
