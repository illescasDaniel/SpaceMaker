# Progress

Open items only. Finished work: `memory/archive.md`.

## SpaceMaker app

- [ ] **USB file transfer (new Home module)** — wireframe approved 2026-09-26; Phase 1 `specs/usb-file-transfer/SPEC.md` drafted on `cursor/usb-file-transfer-c861`; awaiting **spec approval**. Ports/impl not started.
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
- [x] Gallery item detail: photo-app-style open animation (zoom+fade), slide transition on prev/next, and real-thumbnail-first progressive loading while the full image/video loads — full SDD cycle (wireframe → spec → architecture → tests → impl), all gates approved in chat. See `decisions.md` 2026-09-25.
