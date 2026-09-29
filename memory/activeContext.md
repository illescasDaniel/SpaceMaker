_Last updated: 2026-09-29 (session mcp-tools-cache)_

## Branch

`claude/mcp-tools-cache-441056` (forked from `claude/typescript-python-type-hints-0b69dc`) — MCP caching/TS support/bug fixes, gallery delete animation, agent friction log. Not yet applied to `main`.

## Current focus

Wrapping up: everything below is committed and `uv run task checks` + `npm run check` are green. Next: apply to `main`.

## Next steps

- Apply to `main` (`/apply-worktree`).
- Triage `memory/friction/` entries with `status: open` (e.g. give AGENTS.md concrete codenav/webnav example calls; consider accepting `query` as an alias on `selector`/`css_var`).
- Real-app check of the delete animation on the user's library (only fabricated tiles were exercised in the Browser pane).
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).

## Just changed

- MCP fixes: `querySelector` was never indexed; `selector` reports exact-name string literals (helper-passed ids) and labels `[generated]`; inherited `Class.method` via typeHierarchy; `search_symbol` ranks properties last.
- Gallery delete: `removeGalleryItem` (gallery-timeline.ts) fades the tile after the screen fade-in, then removes it in place (no reload/flash, scroll kept); spec `ui-motion` + wireframe updated.
- New `memory/friction/` log + AGENTS.md rule.
