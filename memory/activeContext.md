_Last updated: 2026-09-29 (applied `claude/mcp-tools-cache-441056` to `main`)_

## Branch

`main` (merged `claude/mcp-tools-cache-441056`, on top of `claude/code-grading-sdd-feature-14ecc1`).

## Current focus

Two threads landed together: SDD Phase 5 (`code-grader` + `grade_prechecks.py`) and the MCP/gallery work below. Gate green after merge.

## Next steps

- Trial `code-grader` on the next real SDD feature (confirm the Cursor agent loads).
- Triage `memory/friction/` entries with `status: open` (concrete codenav/webnav example calls in AGENTS.md; maybe a `query` alias on `selector`/`css_var`).
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).

## Just changed

- MCP fixes: `querySelector` indexed; `selector` reports exact-name string literals and labels `[generated]`; inherited `Class.method` via typeHierarchy; `search_symbol` ranks properties last; webnav serves TS; stat-keyed caches.
- Gallery delete: `removeGalleryItem` fades the tile after the screen fade-in, then removes it in place (no reload/flash). Spec `ui-motion` + wireframe updated.
- New `memory/friction/` log + AGENTS.md rule.
- SDD Phase 5 `code-grader`, `managed_tools.py` moved to `bootstrap/services/`, `web/src/*.ts` typing pass (see `decisions.md`).
