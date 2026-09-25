# Progress

Open items only. Finished work: `memory/archive.md`.

## GraphRAG agent tooling

- [ ] `graph.html` generation (`cluster-only` without `--no-viz`) segfaults on this machine (Windows, Python 3.14.6) — worth an upstream report if the interactive visualization is ever wanted
- [ ] No `graphify install --platform agents` (or similar native installer) was used — instructions were hand-written into `AGENTS.md` instead; revisit if Graphify ships a more current native AGENTS.md integration

## SpaceMaker app

- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [x] `reveal_in_file_manager` on Windows raised `CalledProcessError` (500 from `POST /api/gallery/open`) because `explorer /select,` was run with `check=True`; `explorer.exe`'s exit code isn't a reliable success signal. Fixed 2026-09-25 in `src/spacemaker/adapters/outbound/host/open_paths.py` by switching to `check=False`.
- [ ] Photo Backup: uploading a folder from a phone only uploads a single picture instead of the whole folder — reported by user 2026-09-25, not yet diagnosed.
