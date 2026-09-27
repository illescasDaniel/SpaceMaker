# Progress

Open items only. Finished work: `memory/archive.md`.

## SpaceMaker app

- [ ] **ADB Browse / file listing is very slow** — verified working on device (2026-09-27) but FUSE/adbfs dialog and/or `list_file_paths` / extra expansion feel too slow for production. Review before release: batching, shallower walks, shell `find` vs FUSE listing, caching, or skipping adbfs when only transferring known paths. Affects USB file transfer (Android cable).
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
