# Progress

## Initial setup (wireframe gate)

### Done

- [x] Agent governance: AGENTS.md, memory bank, Cursor rules, playbooks, skills
- [x] Reference conversion script in `docs/reference/convert_all_1_1.sh`
- [x] Wireframe `wireframes/app.html` (wizard + gallery)
- [x] Human UX approval of wireframe
- [x] Phase 1 specs under `specs/` (main-wizard, extract-media, convert-media, gallery)
- [x] Human spec approval
- [x] Phase 2: domain types and ports (`src/spacemaker/`)
- [x] Phase 3: unit tests from BDD (`tests/unit/`)
- [x] uv + ruff + ty quality gate; Biome for web assets

### Open

- [x] Wireframe: Step 1 MTP/ADB + info; footer **About & Legal** mini page
- [x] Phase 4 (core): outbound adapters, FastAPI + WebSocket, static UI, desktop entry, integration smoke tests
- [x] Wizard UX: source folders, pause/stop extract, convert gating, device status, warning visibility
- [x] Bundled tools dev workflow (`tools/README.md`, `dev-tools`, no silent PATH in normal dev)
- [x] Convert reliability: nested output dirs, failure surfacing, skip `.thumbnails` (extract + convert)
- [x] Device detection: stale MTP/GVFS + session reconcile; API errors as JSON
- [x] **Gallery / Step 3 Visualize** — status, routing, QR, timeline/calendar, EXIF, thumbs
- [x] **Gallery item page** — preview, metadata, Download + JPEG/MP4 export (server-side, WS progress)
- [x] **Wi‑Fi QR extract (default)** — phone upload session, tokenized LAN `/upload`, MTP/ADB cable modes retained
- [x] Wizard: **Start convert** during active extract stops extract gracefully then converts `originals/`
- [ ] Phase 4 (packaging): PyInstaller, bundled `tools/` in installer, legal assets in bundle
- [x] Specs/docs: bundled third-party tools + legal (privacy, disclaimer, manifest)
