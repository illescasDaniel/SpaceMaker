_Last updated: 2026-09-28_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**codenav/webnav live-test fixes** — ranked search, text errors, dead-server restart, ty root for `mcp-servers` (uncommitted).

## Next steps

- Reload MCP servers so live tools pick up ranking/error handling (verified offline via direct tool-function calls).
- Fix pre-existing ruff/ty gate failures from `42a68fd` (see progress.md).
- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- Mark photo-backup branch ready for review / merge when satisfied.

## Just changed

- `mcp-servers/_shared/errors.py` (new), `format.py` (`rank_workspace_symbols`), `lsp_client.py` (`LanguageServerExitedError`, `is_alive`, `_fail_pending`)
- Both servers: `TOOL_ERRORS` handling, restart dead clients, pass `query` to formatter
- `pyproject.toml` ty root += `./mcp-servers`; integration smoke imports `codenav_mcp.ty_command`
- 7 new unit tests; `docs/agent-tooling.md` updated
