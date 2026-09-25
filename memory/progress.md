# Progress

Open items only. Finished work: `memory/archive.md`.

## GraphRAG agent tooling

- [ ] `graph.html` generation (`cluster-only` without `--no-viz`) segfaults on this machine (Windows, Python 3.14.6) — worth an upstream report if the interactive visualization is ever wanted
- [ ] No `graphify install --platform agents` (or similar native installer) was used — instructions were hand-written into `AGENTS.md` instead; revisit if Graphify ships a more current native AGENTS.md integration

## SpaceMaker app

- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [x] `reveal_in_file_manager` on Windows raised `CalledProcessError` (500 from `POST /api/gallery/open`) because `explorer /select,` was run with `check=True`; `explorer.exe`'s exit code isn't a reliable success signal. Fixed 2026-09-25 in `src/spacemaker/adapters/outbound/host/open_paths.py` by switching to `check=False`.
- [x] Photo Backup: multi-file uploads (e.g. a folder from Android) saved all files but converted only one, leaving the rest unconverted until the user left and re-entered Photo Backup, and the progress bar reset to "0/1" per file instead of showing one running total. Root causes: (1) a self-recursive `start_convert()` call inside `_run_convert` was blocked by its own not-yet-done future; (2) each drain pass reported its own local progress instead of a cumulative total; (3) the convert-trigger fired per uploaded file instead of once per upload batch. Fixed 2026-09-25 in `src/spacemaker/bootstrap/services.py` (drain loop, cumulative progress offset, `maybe_start_convert_drain()` made public and called once per `/api/upload` request in `src/spacemaker/adapters/inbound/web/app.py`). Awaiting user confirmation on real Android hardware.
