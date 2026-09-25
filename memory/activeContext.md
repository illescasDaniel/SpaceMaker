_Last updated: 2026-09-25_

## Branch

`main`

## Current focus

No active thread. Just finished: gallery item detail motion (open animation,
prev/next slide transitions, real-thumbnail-first progressive loading) —
full SDD cycle, all gates approved in chat, implemented and verified live in
a browser session (zero console errors, clean Biome lint). Also fixed a
`.gallery-item-stage` horizontal-centering regression found during
verification (CSS `aspect-ratio`/`max-height`/missing-`width` interaction).
See `memory/decisions.md` (2026-09-25) for both.

Files touched: `src/spacemaker/adapters/inbound/web/static/{app.js,
index.html,shell-gallery.css,theme.css}`, `wireframes/app.html`,
`specs/ui-motion/SPEC.md`, `specs/gallery/SPEC.md`, `specs/README.md`.

The separate, pre-existing `webnav` MCP thread (JS/HTML/CSS code nav +
cold-`search_symbol` fix) is also finished and moved to `memory/archive.md`.

## Next steps

- No open thread from this session. Longer-standing open items: see
  `memory/progress.md` (Easy mode import issues; confirming native pywebview
  backends on real Windows/macOS hardware).

## Run

```bash
uv run task spacemaker
uv run task spacemaker-server       # browser-only, no pywebview window
uv run task checks                  # ruff + ty + pytest, works natively on Windows
uv run task smoke                   # real-process server smoke test (subset of checks)
```

## Notes for Claude Code specifically (this machine)

- Project skills live at `.cursor/skills/` (Cursor's convention); Claude Code only
  auto-discovers `.claude/skills/`. Fixed via a real OS symlink
  `.claude/skills -> ../.cursor/skills` (relative target, portable across
  machines/OS). `git checkout` recreates it correctly on any clone.
- This sandboxed browser auto-suppresses native `confirm()`/`alert()` dialogs
  (`confirm()` returns `false`), so exercising a destructive-action UI button
  (e.g. gallery delete) end-to-end needs `window.confirm = () => true`
  monkey-patched first, or calling the underlying API directly.
- No `npm`/`node` on PATH in some sandboxes — check before assuming Biome
  can't run; a recent session had `node_modules/.bin/` populated and
  webnav's Node-based language servers ran fine.
- Older finished threads: `memory/archive.md` and `docs/agent-tooling.md`.
