# Progress

Open items only. Finished work: `memory/archive.md`.

## Transfer files (in flight)

- [x] Phase 0 wireframe — desktop hub tile + `#view-transfer-files`; phone `phone-transfer.html` (approved 2026-09-25)
- [x] Phase 1 spec — `specs/transfer-files/SPEC.md` + home-modules fifth tile (approved 2026-09-25)
- [x] Phase 2 architecture — domain + ContentHasher port + StageTransferItem (awaiting approval)
- [ ] Phase 3 tests
- [ ] Phase 4 implementation

## SpaceMaker app

- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
- [x] Gallery item detail: photo-app-style open animation (zoom+fade), slide transition on prev/next, and real-thumbnail-first progressive loading while the full image/video loads — full SDD cycle (wireframe → spec → architecture → tests → impl), all gates approved in chat. See `decisions.md` 2026-09-25.
