_Last updated: 2026-09-25_

## Branch

`claude/qt-dependency-assessment-knsl0c`

## Current focus

Gallery performance at 50k+ items is done: the full SDD feature (SQLite-backed
derived index, incremental sync, cursor pagination, frontend infinite scroll +
DOM windowing) plus two follow-up bugs found after the fact (the "Loading
more…" spinner staying visible permanently, and the gallery briefly
duplicating after deleting an item from the detail page). Full detail moved to
`memory/archive.md` ("SpaceMaker app — Gallery performance at 50k+ items
(2026-09-25)"); the SDD decision record is in `memory/decisions.md`. Nothing
left to do on this thread. Being committed and pushed now via `/save-changes`.

## Next steps

- No active thread. Next open items (see `memory/progress.md`): Easy mode
  import issues (wireframe approved, spec in progress), and confirming the
  native pywebview backends on real Windows/macOS hardware.

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
- No `npm`/`node` on PATH in this sandbox — Biome checks for web/JS changes
  can't be run here; say so rather than skipping silently.
- Older finished threads: `memory/archive.md` and `docs/agent-tooling.md`.
