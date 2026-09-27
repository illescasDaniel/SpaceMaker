# Progress

Open items only. Finished work: `memory/archive.md`.

## SpaceMaker app

- [x] **USB file transfer (new Home module)** — full SDD on `cursor/usb-file-transfer-c861` (wireframe/spec/architecture approved 2026-09-26; tests + MTP/ADB/AFC `list_file_paths` + production UI/API). Awaiting real-device verification. Merged with latest `main` (Transfer files LAN + Home layout).
- [x] **Gallery orphan cache cleanup** — injective path-mirrored thumbs/exports;
  in-app delete + sync GC for index/thumbs/exports; SPEC + arch approved;
  merged via PR #4 (`1e516d0` on `main`)
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
