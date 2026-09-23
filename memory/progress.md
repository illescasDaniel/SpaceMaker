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
- [x] **Gallery item page** — preview (55vh desktop), on-disk path; desktop Open/folder + friendly export + Delete; phone Download + friendly + Delete
- [x] **Wi‑Fi QR extract (default)** — phone upload session, tokenized LAN `/upload`, MTP/ADB cable modes retained
- [x] Wizard: **Start convert** during active extract stops extract gracefully then converts `originals/`
- [x] **Home modules hub** — four tiles; Photo/USB/receive/send; specs + implementation; WebEngine cache bust; receive open-folder UX
- [x] **Photo backup (Easy UI)** — light module from hub, auto Wi‑Fi receive, convert-as-received, View gallery + Gallery phone-help FAB; LAN mobile shells (upload/gallery)
- [x] **Easy mode image import issue counts** — images in `error/` / `invalid/` totals on Easy home
- [x] **Home modules hub** — four tiles; Photo/USB/receive/send; specs + implementation; WebEngine cache bust; receive open-folder UX
- [x] **Send files (PC → phone)** — empty-folder guard; folder zip downloads; dedupe selection; stable share QR token while adding items
- [x] **App review (security, docs, hygiene)** — loopback desktop APIs, privacy/legal refresh, stale docs, gitignore, dead port/favicons
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [x] **GPU-only video convert** — HW AV1 → HW H.264 → move-as-is; gallery preview gating; MP4 export hidden without HW encoder
- [x] Phase 4 (packaging): portable PyInstaller onefile, managed CLI downloads, legal assets, app icon + favicon
- [x] Linux release: pruned AppDir AppImage (srxy-style), zstd squashfs, tag-only GitHub Actions release
- [x] Version **1.0.0** + maintainer contact in package metadata and About UI
- [x] Specs/docs: bundled third-party tools + legal (privacy, disclaimer, manifest); docs refresh (hub, LAN security, architecture)
- [x] **Public README** — features, getting started, development; Home hub PNG + `uv run task readme-screenshot`
