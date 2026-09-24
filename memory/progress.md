# Progress

## GraphRAG agent tooling (DX/dev-tooling, not a product feature — no Phase Gate)

### Done

- [x] MkDocs knowledge base: `mkdocs.yml` (material theme), `docs/index.md` template, `docs/database.md` / `docs/testing.md` stubs
- [x] Tried a custom `ast`-based `scripts/agent_tools/generate_code_graph.py` + `knowledge_graph.json`, then ripped it out in favor of the official **Graphify** tool (`graphifyy` on PyPI; CLI binary `graphify`)
- [x] `.githooks/pre-commit` (+ `core.hooksPath`, `.gitattributes` LF force) — regenerates `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` via `graphify extract . --code-only` + `graphify cluster-only . --no-label --no-viz`, auto-stages if changed. Verified end-to-end (`explain`/`path`/`query` all confirmed working).
- [x] Consolidated `CLAUDE.md` into `AGENTS.md` (single instructions file, since other agents like Cursor don't read `CLAUDE.md`)

- [x] `AGENTS.md` documents `diagnose multigraph` (trigger-based: big refactors / suspicious query results) and the `save-result`/`reflect` feedback loop; `graphify-out/memory/*.md` + `graphify-out/reflections/LESSONS.md` un-ignored so the loop persists across sessions/branches
- [x] `.claude/rules/*.md` — five hand-maintained native-format copies of `.cursor/rules/*.mdc` (symlinks tried first, didn't load in this environment; see `decisions.md`). Confirmed loading via the user's own `/context` → **Memory files**. `AGENTS.md` documents the dual-maintenance requirement.

### Open

- [ ] `docs/database.md` / `docs/testing.md` still blank templates — fill in when those conventions are actually decided
- [ ] `graph.html` generation (`cluster-only` without `--no-viz`) segfaults on this machine (Windows, Python 3.14.6) — worth an upstream report if the interactive visualization is ever wanted
- [ ] No `graphify install --platform agents` (or similar native installer) was used — instructions were hand-written into `AGENTS.md` instead; revisit if Graphify ships a more current native AGENTS.md integration

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
- [x] **iPhone USB (AFC) extract — Linux trial** — wireframe/specs + `AfcDeviceRepository`, wizard **iPhone (USB)**; PATH tools like libmtp
- [x] **Extract/convert job control + shutdown** — stop extract waits for USB thread; **Stop convert**; `AppServices.shutdown()` + clean desktop exit
- [x] **Desktop CSP** — loopback allows `unsafe-eval` for pywebview bridge; LAN pages stay strict
- [x] **GPU-only video convert** — HW AV1 → HW H.264 → move-as-is; gallery preview gating; MP4 export hidden without HW encoder
- [x] Phase 4 (packaging): portable PyInstaller onefile, managed CLI downloads, legal assets, app icon + favicon
- [x] Linux release: pruned AppDir AppImage (srxy-style), zstd squashfs, tag-only GitHub Actions release
- [x] Version **1.0.0** + maintainer contact in package metadata and About UI
- [x] Specs/docs: bundled third-party tools + legal (privacy, disclaimer, manifest); docs refresh (hub, LAN security, architecture)
- [x] **Public README** — features, getting started, development; Home hub PNG + `uv run task readme-screenshot`
- [x] **Gallery item prev/next** — timeline order; Font Awesome chevrons; grid-centered overlay controls
- [x] **System UI theme** — `theme.css` + `prefers-color-scheme` on desktop and phone shells (no per-module light/dark)
