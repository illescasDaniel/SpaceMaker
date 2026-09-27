# Progress

Open items only. Finished work: `memory/archive.md`.

## SpaceMaker app

- [x] **Photo backup compress preference** — Full SDD (wireframe → spec → architecture → tests → impl) approved in chat 2026-09-26. Compress media checkbox, persistence, tools gate, Easy auto-convert gating.
- [x] **Promote uncompressed + processed/ + Settings chrome** — Full SDD 2026-09-27. Compress-off promotes originals→`processed/`; rename `converted/`→`processed/` (+ migration); sticky Home|Gallery|Settings; clear prefs / reset library / legal / tools; window 1152×864. Awaiting manual smoke + PR.
- [x] **Gallery orphan cache cleanup** — injective path-mirrored thumbs/exports;
  in-app delete + sync GC for index/thumbs/exports; SPEC + arch approved;
  merged via PR #4 (`1e516d0` on `main`)
- [ ] **codenav/webnav MCP harden** — character-offset docs, `path:line:col` headers, LSP error surfacing, diagnostics push fallback, shared formatters, unit tests (plan approved 2026-09-27)
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
