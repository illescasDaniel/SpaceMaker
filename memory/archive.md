# Archive

Finished history moved out of `activeContext.md` and `progress.md`. Not read
at session start — see `.cursor/skills/agent-memory/SKILL.md`. Kept for
reference; entries are grouped by the area they came from, newest additions
at the top of each section.

## GraphRAG agent tooling (DX/dev-tooling, not a product feature — no Phase Gate)

### Done

- [x] MkDocs knowledge base: `mkdocs.yml` (material theme), `docs/index.md` template, `docs/database.md` / `docs/testing.md` stubs
- [x] Tried a custom `ast`-based `scripts/agent_tools/generate_code_graph.py` + `knowledge_graph.json`, then ripped it out in favor of the official **Graphify** tool (`graphifyy` on PyPI; CLI binary `graphify`)
- [x] `.githooks/pre-commit` (+ `core.hooksPath`, `.gitattributes` LF force) — regenerates `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` via `graphify extract . --code-only` + `graphify cluster-only . --no-label --no-viz`, auto-stages if changed. Verified end-to-end (`explain`/`path`/`query` all confirmed working).
- [x] Consolidated `CLAUDE.md` into `AGENTS.md` (single instructions file, since other agents like Cursor don't read `CLAUDE.md`)
- [x] `AGENTS.md` documents `diagnose multigraph` (trigger-based: big refactors / suspicious query results) and the `save-result`/`reflect` feedback loop; `graphify-out/memory/*.md` + `graphify-out/reflections/LESSONS.md` un-ignored so the loop persists across sessions/branches
- [x] `.claude/rules/*.md` — five hand-maintained native-format copies of `.cursor/rules/*.mdc` (symlinks tried first, didn't load in this environment). Confirmed loading via the user's own `/context` → **Memory files**. Later (2026-09-24, "lean agent context" refactor) reduced to a single path-scoped `hexagonal-python` pair; the rest merged into `AGENTS.md` or skills — see `decisions.md`.
- [x] `docs/testing.md` populated for real (BDD given/when/then, mocking standards) — no `docs/` pages left as blank stubs; `docs/database.md` was added then removed the same session (SpaceMaker has no database)

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
- [x] **Send files (PC → phone)** — empty-folder guard; folder zip downloads; dedupe selection; stable share QR token while adding items
- [x] **App review (security, docs, hygiene)** — loopback desktop APIs, privacy/legal refresh, stale docs, gitignore, dead port/favicons
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
- [x] **QtWidgets native dialog style** — `windows11`/Fusion `QStyle` via `qt_native_style.py`
- [x] **Windows WebEngine freeze/black-surface bug** — `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu-compositing` (win32-only) in `qt_webengine_gpu_flags.py`; user-confirmed fixed. Two prior attempts (`--use-angle=d3d9`, `QSG_RHI_BACKEND=opengl`) ruled out, see `decisions.md`
- [x] **Windows ProactorEventLoop ConnectionResetError noise** — uvicorn switched to SelectorEventLoop on win32 via `event_loop.uvicorn_loop_for_platform()` (`"asyncio:SelectorEventLoop"` string directly; a first attempt via a wrapper function broke startup entirely — see `decisions.md`)
- [x] **Real-process smoke test** — `tests/integration/test_server_smoke.py` + `uv run task smoke`; boots `python -m spacemaker --server-only` for real and polls it, catching startup/wiring bugs `TestClient`-based tests can't see
- [x] **`QDxgiVSyncService`/`QThreadStorage` shutdown warnings investigated** — confirmed benign/cosmetic, confirmed unrelated to (not fixed by) the WebEngine freeze fix; accepted, not pursuing further unless it becomes more than log noise — see `decisions.md`

## activeContext threads (concluded)

### 2026-09-24 — Graphify tooling adoption + `.claude/rules/` mirroring

Adopted Graphify's `diagnose multigraph` and `save-result`/`reflect`
feedback loop (documented in `AGENTS.md`, committed `b022d49`), then mirrored
`.cursor/rules/*.mdc` into Claude Code's new `.claude/rules/` directory.
Symlinks (both a blind directory link and per-file `.md`-renamed links)
didn't load in this environment — replaced with five hand-maintained native
`.md` copies, confirmed loading via the user's own `/context` → **Memory
files**. `AGENTS.md` documented the dual-maintenance requirement at the
time (edit both `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md`
together). Superseded 2026-09-24 by the "lean agent context" refactor,
which reduced the five rule pairs to one (`hexagonal-python`, path-scoped)
and merged the rest into `AGENTS.md` or skills — see `decisions.md`.

### 2026-09-24 — GraphRAG worktree applied to main

Applied the `claude/graphrag-mkdocs-codebase-graph-891193` worktree onto
`main` via `/apply-worktree`: agent-facing GraphRAG tooling — an MkDocs
knowledge base (`docs/`) and a codebase dependency graph via the official
**Graphify** tool (`graphifyy` on PyPI; CLI is `graphify`), wired into a
version-controlled `.githooks/pre-commit` so the graph stays synced with
every commit on both Windows and Linux. Dev-tooling, not a product feature,
so it didn't go through the Phase Gate Protocol (wireframe/spec/architecture).

### 2026-09-24 — `.claude/skills` symlink repointed for portability

On `main` itself: the `.claude/skills` symlink was repointed to a relative
target (`../.cursor/skills`) for cross-machine portability (commit
`87b2196`) — see `decisions.md` for the `New-Item` directory-symlink pitfall
discovered along the way.

### Gotchas discovered (moved to `docs/agent-tooling.md`)

The durable Graphify/Windows gotchas from this thread (PyPI package name,
`--no-viz` segfault, case-insensitive `docs/` filename collision,
`mklink /D` vs `New-Item`) are reference material, not session state — see
`docs/agent-tooling.md` "Windows / tooling gotchas" instead of this file.
