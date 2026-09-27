_Last updated: 2026-09-27_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Saving promote/processed + Settings chrome** — feature Phases 0–4 complete; committing and pushing, then hardening codenav/webnav MCP (approved plan: character-offset columns, `path:line:col` headers, LSP error surfacing, diagnostics push fallback, shared formatters, unit tests).

## Next steps

- After push: implement MCP nav improvements plan.
- Manual check: Settings → Clear preferences — list width must stay put (reload if CSS cached).
- Manual check: upload with Compress off → photo in Gallery; sticky header scroll.
- Optional: migrate local library `converted/` → `processed/` (also auto on `ensure_library_folders`).
- Mark ready for review / merge when satisfied.

## Just changed (this commit)

- `LibraryFolder.PROCESSED`; promote-originals when compress off; Clear prefs / Reset library APIs
- Sticky Settings chrome; window 1152×864; `.screen` width fix (list no longer widens on confirm)
- MCP: `workspace.py` root resolution + Cursor/Claude mcp.json env pins
