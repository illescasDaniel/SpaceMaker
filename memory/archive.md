# Archive

Finished history moved out of `activeContext.md` and `progress.md`. Not read
at session start — see `.cursor/skills/agent-memory/SKILL.md`. Kept for
reference; entries are grouped by the area they came from, newest additions
at the top of each section.

## SpaceMaker app — Gallery performance at 50k+ items (2026-09-25)

### Done

- [x] **Core perf work:** SQLite-backed derived index (`GalleryIndexPort`/`SqliteGalleryIndex` at `{library_root}/.index.sqlite`, filesystem stays source of truth), incremental sync (`SyncGalleryIndex`, diffs `converted/` by `(mtime, size)`, only re-probes EXIF for added/changed files instead of the whole library on every change), cursor-paginated `/api/gallery/timeline` (compound `(captured_at, relative_path)` keyset — ties are real, e.g. every EXIF-probe failure shares the same fallback timestamp), new `/api/gallery/item/neighbor` endpoint (replaces holding a full client-side path array for Prev/Next), frontend infinite scroll (`IntersectionObserver` + sentinel) and DOM windowing at month-block granularity (~1200-tile mount budget) in `app.js`. Full SDD cycle (Phase 0 wireframe → Phase 4 implementation), all gates explicitly approved in chat 2026-09-25. `to_epoch_seconds`/`from_epoch_seconds` (`domain/gallery_index.py`) use a fixed UTC offset rather than `datetime.timestamp()`/`fromtimestamp()`, which go through the OS's local `mktime` and raise `OSError` on Windows for dates at/before 1970. Found and fixed a real `sqlite3.InterfaceError` concurrency bug via manual browser testing (concurrent Prev/Next `neighbor` requests shared one `sqlite3.Connection` without a query-level lock; fixed with a reentrant `threading.RLock` wrapping every `SqliteGalleryIndex` public method, plus a multi-thread regression test) — not caught by any unit test, only by real concurrent HTTP requests in a real browser. Full decision record: `memory/decisions.md` "2026-09-25 — Gallery at 50k+ items". 208 tests passing, ruff/ty clean, Biome clean (0 new errors/warnings vs. the pre-existing baseline, diffed via `git stash` before/after).
- [x] **Follow-up bug — spinner always visible:** the "Loading more…" indicator sat visible at the top of the timeline permanently instead of only while fetching (or hidden with nothing left to load). `.gallery-loading-more { display: flex; }` — duplicated in `index.html`'s inline `<style>` (what the desktop app actually renders) and `shell-gallery.css` (used by `gallery_mobile.html`) — unconditionally overrode the browser's built-in `[hidden] { display: none }` UA rule, since author CSS always wins over UA styles regardless of selector specificity; `app.js` was already correctly toggling `el.hidden`, it just had no effect. Fixed by adding `.gallery-loading-more[hidden] { display: none; }` next to each duplicate. Verified live: computed `display` went `flex` → `none`, Biome clean (only pre-existing, unrelated warnings elsewhere in `index.html`).
- [x] **Follow-up bug — gallery duplicated after deleting an item:** deleting an item from the detail page briefly showed the whole gallery overview duplicated (every thumbnail twice), self-correcting on the next visit. `btn-gallery-delete`'s click handler in `app.js` called `showView("gallery")` *and then* `loadGallery()` — but `showView()` already calls `loadGallery()` internally for the gallery view, which every other call site (back button, Home/Gallery tabs) already relied on without calling it again. The two synchronous `loadGallery()` calls each reset state and fired their own first-page fetch; both later resolved and each appended the same items, hence the ×2 duplication. Fixed by removing the redundant `loadGallery()` call. Reproduced conclusively with a disposable copied-in test file (never touched the user's real library photos): 39 real items → 78 DOM thumbnails (exactly ×2) with the old code, back to 39/no dupes after the fix — confirmed via direct `DELETE /api/gallery/item` API calls plus a real UI click-through with `window.confirm` monkey-patched, since this sandboxed browser auto-suppresses native `confirm()`/`alert()` dialogs (returns `false`), so any future gallery delete/destructive-action UI testing here needs the same workaround. Biome clean on `app.js`.

## SpaceMaker app — Windows hardware fixes (2026-09-25, pre-gallery-perf session)

### Done

- [x] `reveal_in_file_manager` on Windows raised `CalledProcessError` (500 from `POST /api/gallery/open`) because `explorer /select,` was run with `check=True`; `explorer.exe`'s exit code isn't a reliable success signal. Fixed in `src/spacemaker/adapters/outbound/host/open_paths.py` by switching to `check=False`.
- [x] Photo Backup: multi-file uploads (e.g. a folder from Android) saved all files but converted only one, leaving the rest unconverted until the user left and re-entered Photo Backup, and the progress bar reset to "0/1" per file instead of showing one running total. Root causes: (1) a self-recursive `start_convert()` call inside `_run_convert` was blocked by its own not-yet-done future; (2) each drain pass reported its own local progress instead of a cumulative total; (3) the convert-trigger fired per uploaded file instead of once per upload batch. Fixed in `src/spacemaker/bootstrap/services.py` (drain loop, cumulative progress offset, `maybe_start_convert_drain()` made public and called once per `/api/upload` request). Verified: ruff clean, 179 passed / 5 pre-existing skips. Still awaiting user confirmation on real Android hardware — no open tracking item needed beyond this note since it's a one-off verification, not further dev work.
- [x] Dropped Qt as a forced dependency on Windows/macOS — pywebview now uses native backends there (WebView2 `edgechromium` on Windows, WKWebView `cocoa` on macOS); Linux keeps Qt WebEngine (AppImage pins a known Chromium version). See `decisions.md` ("Native pywebview backend on Windows/macOS; Qt WebEngine kept Linux-only"). Real-hardware WebView2/WKWebView window creation was smoke-tested only via `--server-only` (no GUI in this sandbox) — genuinely unverified on real Windows/macOS hardware; if this surfaces again, check with the user whether it's been confirmed working before assuming it still needs testing.

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
- [x] **`QDxgiVSyncService`/`QThreadStorage` shutdown warnings** — confirmed benign/cosmetic, confirmed unrelated to (not fixed by) the WebEngine freeze fix; teardown timing left as-is, but the two known-benign lines are now filtered via a `qInstallMessageHandler` wrapper in `qt_webengine_shutdown.py` so they no longer print; user-confirmed — see `decisions.md`

### 2026-09-24 — Windows desktop-bug dogfooding round (freeze, event-loop noise, shutdown warnings, native style)

Fixed three Windows-only desktop/server bugs found while dogfooding `uv run task spacemaker` (Chromium/Qt-WebEngine GPU-compositor freeze fixed by `--disable-gpu-compositing`; noisy `ConnectionResetError` tracebacks fixed by pointing uvicorn's `loop=` at `"asyncio:SelectorEventLoop"` directly, after a first attempt using a wrapper function broke the app outright — root-caused and fixed, verified against a new `tests/integration/test_server_smoke.py` real-process smoke test; non-native pywebview dialogs themed via `qt_native_style.py`). Landed as commit `176db11`. Full root causes in `decisions.md`.

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
