_Last updated: 2026-10-03 (jevmem trial: memory placement rule, auto recall default)_

## Branch

`feature/jevmem-trial`. Trial wiring of jevmem from the local `~/Projects/Code/Python/Jev-things` checkout (`.mcp.json`, `.claude/settings.json` hooks, `.cursor/skills/jev-memory/`); the uncommitted `.mcp.json` codenav change and `memory/mcp-write-tools-trial.md` belong to the separate codenav write-tools trial.

## Current focus

jevmem trial. Done this session: fixed the MCP thread-bound SQLite bug (every tool could fail; `memory_pin` did), pinned notes 42/43/45, `auto` is the default recall mode, and the "what goes where" rule (state → this folder, dated facts → jevmem, rules → AGENTS.md) is in AGENTS.md, both memory skills and `decisions.md`. Jev-things changes are uncommitted.

Next: restart the jevmem MCP server (picks up the thread fix and `auto`), then tackle the new jevmem README known limitations (per-branch scope, stale status notes, instructions-file filter misses, hidden MCP errors).

## Just changed

- Gallery item **Open in Maps ↗** button (spec `gallery-open-in-maps`), uncommitted: `web/src/gps.ts`, `domain/map_link.py`, `OpenMapLocation`, `DesktopApi.open_external_url`, tests in `web/tests/gps.test.ts` + `tests/unit/test_open_map_location.py`.

- Unlock page CSS/JS externalized (`static/unlock.css`, `web/src/unlock.ts`); exempt paths are exactly `/api/unlock`, `/favicon.ico`, `/static/unlock.css`, `/static/js/unlock.js` (spec line updated, approved).
- First JS tests: vitest + jsdom in `web/tests/` (`npm run test:web`, part of `npm run check`). Info button fixed (`.info-panel.visible`), dock Active copy is now "Active".
- Earlier: pre-1.0 review fixes and `convert-media` spec amendments (see `progress.md`).

## Release 1.0.1 (2026-10-02)

`appimage.yml` → `release.yml` (Linux AppImage + Windows exe + macOS arm64/x86_64 DMGs, combined `SHA256SUMS`); version bumped to 1.0.1. Windows/macOS CI jobs unverified until a `workflow_dispatch` dry run passes; then tag `v1.0.1`.

## Next steps

1. User reviews the passcode feature (click the dock info button in the real app).
2. Add JS tests for other `web/src` modules (start with `dom.ts`).
3. Still open (deliberately skipped): tool catalog sha256 pinning, ADB list-all-roots speed-up, LAN delete/export auth beyond the passcode.
