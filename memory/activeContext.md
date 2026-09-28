_Last updated: 2026-09-28_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Photo-backup branch** — MCP servers split into a uv workspace (`mcp-nav-shared`, `codenav-mcp`, `webnav-mcp`); quality gates green. PR merge in progress after `/save-pr-changes`.

## Next steps

- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- After merge: reload codenav/webnav MCP in Cursor (launch is now `python -m codenav_mcp.server` / `python -m webnav_mcp.server`), then live re-verify: `diagnostics(transfer.html)` → no warnings; `diagnostics(wireframes/app.html)` → only `.disconnected`/`.alert-actions`/`.ui-mode-toggle`; `selector(".slide-in-next-start")` shows a `class-var +=` JS hit.

## Just changed

- **mcp-servers → uv workspace** (2026-09-28): three installable packages under `mcp-servers/{_shared,codenav_mcp,webnav_mcp}/` with `src/<pkg>/` layouts, workspace deps via `tool.uv.sources`, MCP configs updated to `python -m <pkg>.server`, tests relocated per package. `uv run task checks` green (382 pytest + Biome).
