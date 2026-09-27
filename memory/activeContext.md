_Last updated: 2026-09-27_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**codenav/webnav MCP harden** — character-offset columns, `path:line:col` headers, LSP error surfacing, diagnostics push fallback, shared formatters, unit tests.

## Next steps

- Commit + push MCP harden (after checks).
- Manual re-smoke MCP tools if Cursor reloads servers (optional).
- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- Mark photo-backup branch ready for review / merge when satisfied.

## Just changed

- `_shared/format.py`; `LspRequestError`; diagnostics cache fallback; both MCP servers use shared formatters + clearer docs
- `docs/agent-tooling.md` Positioning section
- `tests/unit/test_mcp_nav_format.py` (10 fast tests)
- Prior commit `42a68fd`: processed/, promote-originals, Settings chrome, MCP workspace root
