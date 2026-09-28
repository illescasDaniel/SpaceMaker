_Last updated: 2026-09-28_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Photo backup PR #2** — merged `origin/main` (USB file transfer + MCP uv workspace on branch); landing via `/save-pr-changes`.

## Next steps

- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- After merge: reload codenav/webnav MCP (`python -m codenav_mcp.server` / `python -m webnav_mcp.server`).

## Just changed

- Merge `origin/main` into photo-backup branch (USB transfer + Settings/processed/`compress_media` combined).
- Commit `ef5d6e5`: mcp-servers uv workspace (382 tests + Biome green).
