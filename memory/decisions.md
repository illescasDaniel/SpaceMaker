# Technical decisions

Append-only log (newest first). Never rewrite history.

## 2026-09-24 — `graphify-out/graph.json` / `GRAPH_REPORT.md` will always show an unstaged diff right after a commit — expected, not a bug

- **Context:** After committing GraphRAG tooling (see the entry below), `git status` showed `graphify-out/graph.json` (later `GRAPH_REPORT.md`) as modified immediately post-commit, on both occasions. Investigated via file mtime vs. commit timestamp rather than assuming it would go away.
- **Finding:** `.githooks/pre-commit` runs *before* Git creates the new commit object, so `git rev-parse HEAD` inside the hook can only ever see the **parent** commit — the new commit's hash doesn't exist yet (it's derived from the tree, so a tracked file can never embed its own containing commit's hash; that's a hash-cycle, not a missing feature). Graphify's `built_at_commit` field therefore always lands one commit behind in what actually gets committed. Separately, Graphify's clustering step re-touches the file a few seconds *after* the hook's `git add` (confirmed via mtime: file changed ~3s after the commit timestamp), re-stamping it with `HEAD` as of that moment — which by then is the *new* commit, since the ref already advanced. That second, unstaged write is the actual diff `git status` shows.
- **Decision:** Documented instead of "fixed" — there is nothing to fix. Re-running the hook or re-committing does not resolve it; it reproduces the identical one-commit-behind drift on the *next* commit. Don't spend time chasing this again.
- **Rationale:** Any tool that stamps a generated artifact with "the commit that produced me" has this same inherent limitation. Silently accepting a permanently-slightly-dirty `git status` after touching graph files is less confusing than a future session assuming it's a regression and trying to patch it.

## 2026-09-24 — GraphRAG agent tooling: MkDocs + Graphify (not custom AST script), CLAUDE.md merged into AGENTS.md

- **Context:** Built agent-facing "GraphRAG" tooling so AI agents can orient in this codebase without broad file reads: an MkDocs knowledge base and a structural dependency graph. First pass used a hand-rolled `ast`-based script (`scripts/agent_tools/generate_code_graph.py` → `knowledge_graph.json`); a later instruction said to rip that out and use the official open-source "Graphify" tool instead, with the exact package name `graphify`.
- **Decision:** Verified `graphify` does not exist on PyPI (404) before installing anything — the real, legitimate package (121k★ GitHub repo, YC-backed, matches the described `explain`/`path`/`query` + `graph.json`/`GRAPH_REPORT.md` CLI exactly) is `graphifyy` (double-y; the CLI binary it installs is `graphify`). Installed that instead and flagged the correction. Deleted the custom script/`knowledge_graph.json`. `.githooks/pre-commit` (version-controlled, activated via `git config core.hooksPath .githooks` — see prior symlink-discovery entry on why this repo avoids relying on `.git/hooks/`) now runs `graphify extract . --code-only` then `graphify cluster-only . --no-label --no-viz` (the no-LLM-API-key pipeline; `--no-viz` avoids a native segfault on this Windows/Python-3.14.6 setup) and auto-stages `graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md` if changed. Separately, merged `CLAUDE.md`'s content into `AGENTS.md` and deleted `CLAUDE.md`, since the user also drives this repo from Cursor and other agents that only read `AGENTS.md`.
- **Rationale:** Installing an unverified/mistyped package name and wiring it into a hook that auto-executes on every future commit on both the user's Windows and Linux machines is a real supply-chain risk surface — worth a PyPI/GitHub legitimacy check before `uv add`, not after. The custom AST script was reasonable as a first pass but strictly worse than the real tool once available (no fully-qualified node IDs, best-effort name-only call matching, no query/path/explain CLI). A single `AGENTS.md` avoids the two-file drift risk that motivated the earlier "did not add a `CLAUDE.md` symlink" non-decision — now there's nothing for it to drift from.



## 2026-09-24 — Windows portable build reliability batch (QR, component downloads, shutdown)

- **Context:** Windows dogfooding surfaced four separate rough edges in the portable build: QR codes rendered with a theme-matched (often dark) background so they were unreadable in dark mode and briefly flashed/collapsed on `src` reload; the packaged ffmpeg download URL and the ImageMagick/ExifTool story were incomplete for Windows (no ExifTool catalog entry, no fallback when winget installs ImageMagick without updating `PATH`); `start_convert`'s `STOP_EXTRACT_FIRST` policy called `stop_extract_and_wait()` unconditionally, which dropped the Easy-mode Wi‑Fi upload session on the very first "convert as received" trigger even when no extract job was actually running; and Qt WebEngine/Chromium left native threads/timers that could hang or crash on quit, worse on Windows than Linux.
- **Decision:** `adapters/inbound/web/qr_svg.py` wraps `segno` with explicit opaque `dark="#000000"/light="#ffffff"` and callers set `background: #fff` around the `<img>`; `app.js` gets a `setQrImageSrc()` helper that only reassigns `img.src` when the QR URL actually changed (was unconditional reassignment every poll, causing the flash). `packaging/tool-catalog.json` adds an `exiftool` entry via new `CatalogToolInstaller` `zip_flatten` strategy (flattens a zip's `prefix/` into the tools dir and copies a `launcher` file to the canonical bundled name); `bundled_tools.py` adds `_windows_magick_from_common_install_dirs()` (Program Files glob, PATH fallback) and `bootstrap/platform_setup_hints.py` returns a winget one-liner for the Components screen when ffmpeg/magick/exiftool are missing on Windows. `AppServices.start_convert` now only calls `stop_extract_and_wait()` under `STOP_EXTRACT_FIRST` when `self._extract_job_active()` is true.
- **Rationale:** Each fix is independently small but all were discovered together while validating the Windows portable build end-to-end; grouping them avoided four near-identical "Windows build fix" commits touching overlapping files (`app.js`, `index.html`).

## 2026-09-24 — Qt WebEngine shutdown teardown hardened further for Windows

- **Context:** The existing `install_qt_webengine_shutdown_fix()` (page/profile `deleteLater` + a short `processEvents` drain) was tuned on Linux; on Windows it still left the process hanging or crashing on quit because WebChannel/nav-handler objects, top-level widgets, and the URL request interceptor were never explicitly torn down, and Windows needs longer event-drain rounds plus real `time.sleep` gaps for `QDxgiVSyncService` to unwind asynchronously.
- **Decision:** `_tear_down_webview` is now idempotent (`_spacemaker_webengine_torn_down` guard) and additionally disconnects webchannel/nav-handler/cookie-store signals, tears down the request interceptor, and deletes top-level widgets; new `finalize_qt_after_webview()` runs after pywebview's own event loop exits (called from `desktop.py` `main()` before `_shutdown_services` and `os._exit(0)`). Round/delay counts are platform-tuned via `_shutdown_event_rounds()` / `_shutdown_quit_delay_ms()` / `_shutdown_finalize_passes()` (higher on `win32`).
- **Rationale:** `os._exit(0)` was already accepted as the pragmatic hard-exit (uvicorn's daemon thread can't be joined without a bigger refactor); this change reduces how much unclean Chromium/Qt state that hard exit has to paper over, rather than replacing it.

## 2026-09-24 — Claude Code project-skill discovery via `.claude/skills` symlink

- **Context:** This repo's skills live under `.cursor/skills/<name>/SKILL.md` (Cursor's convention, per `AGENTS.md`'s Skills section). Claude Code's desktop app (Code tab) never showed `/save-changes`, `/apply-worktree`, etc. in autocomplete — it only auto-discovers project skills from `.claude/skills/`, with no fallback to `.cursor/skills/` the way it falls back from `CLAUDE.md` to `AGENTS.md` for instructions.
- **Decision:** Create a real OS-level directory symlink `.claude/skills -> .cursor/skills` (needs an elevated PowerShell: `New-Item -ItemType SymbolicLink -Path ".claude\skills" -Target ".cursor\skills"` after `mkdir .claude`). `core.symlinks=true` is already set for this repo, so git tracks it as one `120000` symlink blob rather than duplicating every `SKILL.md`.
- **Rationale:** A plain copy (`.claude/skills/*` duplicated from `.cursor/skills/*`) was rejected — it would drift out of sync on every future skill edit. Git Bash's `ln -s` silently falls back to a real recursive **copy** without elevated privileges/Developer Mode on Windows (confirmed: no `LinkType`, git staged `100644` not `120000`) — must use `New-Item -ItemType SymbolicLink` (or `mklink /D`) from an elevated shell, not `ln -s`, to get an actual symlink on this OS.
- **Related non-decision:** Did **not** add a `CLAUDE.md -> AGENTS.md` symlink — Claude Code already reads `AGENTS.md` natively when no `CLAUDE.md` exists (confirmed: this session loaded `AGENTS.md` as project instructions with no `CLAUDE.md` present), so that fallback needs no extra plumbing, unlike skills.

## 2026-09-24 — `uv run task checks` dispatches via bash on native Windows

- **Context:** `scripts/quality/checks.py` ran `checks.sh` directly as `subprocess.call([str(script)], ...)`, which relies on the POSIX shebang; on native Windows Python (not inside Git Bash) this fails with `OSError: [WinError 193] %1 is not a valid Win32 application`, silently blocking the whole quality gate (ruff/ty/pytest/web) for anyone running `uv run task checks` from PowerShell/cmd.
- **Decision:** When `sys.platform == "win32"`, prepend `shutil.which("bash")` to the command (erroring clearly if bash isn't on `PATH`); Unix keeps calling `checks.sh` directly.
- **Rationale:** `checks.sh` itself is fine under bash (verified — ruff/ty/pytest/web all pass on Windows via Git Bash); the dispatcher just needed to route through an interpreter that understands the shebang. Git Bash is already assumed elsewhere in this repo's Windows workflow.

## 2026-09-23 — System theme and self-hosted Font Awesome for gallery nav

- **Context:** Per-module light vs dark palettes diverged from user expectation; gallery prev/next used hard-coded dark overlays with poor contrast in light mode; chevron alignment was off with absolute positioning.
- **Decision:** Single `theme.css` with `prefers-color-scheme` for all shells; remove `syncShellTheme` / gallery-system-theme overrides. Gallery nav uses CSS grid overlay + vendored Font Awesome Free solid chevrons under `static/vendor/fontawesome/` (CSP `font-src 'self'`).
- **Rationale:** Matches OS appearance everywhere; keeps LAN/desktop offline-capable without CDN; grid `align-self: center` tracks preview height reliably.

## 2026-09-23 — LAN server: loopback-only desktop control plane

- **Context:** FastAPI binds `0.0.0.0` for phone QR/LAN gallery, but mutating APIs, `GET /api/settings`, and `/ws` exposed full session state (including upload/receive/share token URLs) to any LAN client.
- **Decision:** `require_loopback()` on `request.client.host` for desktop control APIs and WebSocket; phone gallery (list/media/thumbs/delete/export) and tokenized upload/receive/share stay reachable on LAN; drop `library_root` query override on gallery endpoints; resolve converted paths with `Path.relative_to`.
- **Rationale:** Matches trusted-PC / untrusted-LAN model without adding gallery QR tokens (product choice deferred).

## 2026-09-23 — Send files: folder zips and stable LAN share token

- **Context:** Phone download listed every file inside a shared folder; adding items regenerated the share token and forced a new QR scan; canceling the folder picker duplicated the last path.
- **Decision:** Manifest is one row per top-level selection (file or `folder_zip`); folders download as on-demand `.zip` with preserved relative paths. Share `?t=` token is created on first item and reused until Clear/Home/quit. Selection dedupes by resolved path; share folder picker returns empty string on cancel.
- **Rationale:** Matches user mental model (one folder → one download); one QR session for batch sharing from desktop.

## 2026-09-23 — Desktop window 4:3 geometry in one module

- **Context:** Default pywebview size (980×920) felt narrow; README screenshot script duplicated width/height literals.
- **Decision:** `bootstrap/window_geometry.py` defines **1200×900** default and **800×600** minimum (both 4:3); `desktop.py` and `capture_readme_home_screenshot.py` import from there.
- **Rationale:** More horizontal room for hub/wizard layout; single source of truth for viewport parity between app and docs capture.

## 2026-09-23 — README Home screenshot via offscreen WebEngine

- **Context:** Public GitHub release needs a committed Home hub hero image that stays in sync with production UI without manual window grabs or CI WebEngine deps.
- **Decision:** `scripts/packaging/capture_readme_home_screenshot.py` starts `--server-only` in an isolated `HOME`, `POST /api/tools/components-continue`, renders at 980×920 with PyQt6 `QWebEngineView` (`QT_QPA_PLATFORM=offscreen` default); output `docs/assets/readme-home.png`; task `uv run task readme-screenshot`. Not run in AppImage CI.
- **Rationale:** Same HTML as desktop; repeatable for contributors; avoids OS window-manager automation.

## 2026-09-23 — Linux 1.0 release: AppDir AppImage and tag-only CI

- **Context:** PyInstaller onefile AppImages were large (~256 MB) and double-compressed; srxy uses relocatable AppDir + Qt prune; `.xz` wrap saved ~2 MB for noticeable CPU/time.
- **Decision:** Primary Linux artifact = pruned AppDir + squashfs zstd‑19 AppImage; `SHA256SUMS` on the `.AppImage` (no `.xz`). GitHub Actions `.github/workflows/appimage.yml` runs only on `v*` tags (+ optional `workflow_dispatch`), uploads artifact, attaches to GitHub Release. Version **1.0.0** and maintainer contact centralized in `app_meta` / `pyproject.toml`.
- **Rationale:** WebEngine floor limits shrink margin; AppDir avoids onefile overhead; tag-only CI matches release cadence and avoids main-branch build cost.

## 2026-09-23 — Home hub modules and Qt WebEngine shell cache

- **Context:** Single default UI needed distinct flows (photo backup, USB wizard, receive/send files); pywebview kept serving stale HTML/JS while the browser showed updates.
- **Decision:** `AppModule` + one LAN session at a time; Home hub tiles; phone `/receive` and `/share` pages; `UI_SHELL_VERSION` drives a versioned WebEngine profile dir and `?_shell=` entry URL; no-cache headers on shell assets. Receive **Open documents folder** opens `{Documents}/SpaceMaker` when present, else Documents; Linux `xdg-open` targets directories directly (not parent only).
- **Rationale:** Clear module boundaries; avoids silent cache mismatch in desktop shell; file-manager open matches user path expectations on Linux.

## 2026-09-22 — Portable release: managed CLI downloads (not bundled in exe)

- **Context:** Public release should be a single portable executable without embedding large third-party CLIs; users still need pinned, working dependency versions.
- **Decision:** Download pinned tools into OS-specific user data dirs (`managed_tools_dir()`); resolution order managed → catalog download → `PATH`; Components UI on first run; About & Legal **Delete downloaded components**. Catalog in `packaging/tool-catalog.json`; ffmpeg/ffprobe via `static-ffmpeg` PyPI wheel; adb via versioned platform-tools zip. No traditional installer. Reverses “bundle all CLIs inside artifact” v1 decision.
- **Rationale:** Smaller portable binary; updatable pins; graceful fallback when upstream download fails; aligns with user-requested portable model.

## 2026-09-22 — GPU-only library video convert and gallery preview gating

- **Context:** CPU AV1/x264 encodes are slow and HEVC library outputs do not preview in the web gallery; users on machines without HW encoders still need files in `converted/`.
- **Decision:** Detect ffmpeg HW encoders once per process: AV1 (nvenc/qsv/vaapi) preferred, else H.264 HW → `{stem}.h264.mp4`; else move video to `converted/` unchanged. Friendly MP4 export uses the same HW H.264 path; UI hides **Download as MP4** when no HW encoder. Gallery item API exposes `preview_in_browser` (excludes HEVC). Easy mode shows image-only counts in `error/` and `invalid/`.
- **Rationale:** Matches web playback constraints; avoids silent CPU transcodes; keeps Easy users informed without a full bucket browser.

## 2026-09-22 — Gallery item delete and Web Share export

- **Context:** Item page needed host path visibility, safe removal from `converted/`, and phone-friendly sharing without manual download steps.
- **Decision:** `GetGalleryItem` returns `absolute_path`; `DeleteGalleryItem` + `DELETE /api/gallery/item`. Desktop uses `POST /api/gallery/open` (xdg-open / OS reveal) instead of raw Download/Share; phone shell keeps Download + friendly export only. Stub `GET /json/version` for Chromium probe noise. HTML shells use default caching (no forced no-cache).
- **Rationale:** Shell-specific markup; host actions on PC only; avoid uvicorn 404 spam without hurting reload performance in production.

## 2026-09-22 — Start convert stops active extract

- **Context:** Users may want to convert files already in `originals/` without manually stopping extract first (common during Wi‑Fi receive).
- **Decision:** `can_start_convert` depends only on `originals/` count. `start_convert` calls `stop_extract_and_wait()` (graceful stop + USB thread join + Wi‑Fi in-flight drain) before starting convert.
- **Rationale:** One-click flow; avoids racing extract writes against convert reads.

## 2026-09-22 — Wi‑Fi extract as default (tokenized LAN upload)

- **Context:** USB MTP/ADB friction; users want cable-free transfer from any phone browser on the same LAN.
- **Decision:** `ConnectionMethod.WIFI` default on Step 1; **Start extract** mints a session token in the upload QR/URL; multipart POST to `/api/upload` writes to `originals/` via `ReceiveUploadedMedia` + `FileSystemPort.copy_file`. Move disabled for Wi‑Fi. USB paths unchanged. Dependency: `python-multipart`.
- **Rationale:** Reuses existing LAN bind and segno QR pattern; no open LAN ingest without an active session; hexagonal split (no `DeviceRepository` for Wi‑Fi).

## 2026-09-22 — SDD: explicit design + spec approval before src

- **Context:** Agents sometimes ran wireframe → spec → full implementation in one pass when the user attached a plan or said “implement the plan.”
- **Decision:** Phase gates in `AGENTS.md`, `sdd.mdc`, and `sdd-feature` skill require **explicit chat confirmation** after wireframe (design) and after spec before production source (`src/spacemaker/`, production static UI). Attached plans/todos are not substitutes for those approvals.
- **Rationale:** Keeps UX and behavioral truth in human-reviewed artifacts; reduces silent drift from wireframe/spec.

## 2026-09-22 — Gallery export separate from library convert

- **Context:** Users need Download-as-JPEG/MP4 on the item page without changing AVIF/AV1 library policy or size rollback.
- **Decision:** On-demand `ExportFriendlyMedia` (Magick q95 JPEG, ffmpeg libx264 CRF 18 + AAC); cache under `{library}/.exports/`; skip encode when already JPEG or H.264+AAC MP4; progress via WebSocket `gallery_export` events.
- **Rationale:** Keeps convert pipeline unchanged; quality-first exports; same skip rules as `.thumbnails` for scans.

## 2026-09-22 — LAN firewall probe in bootstrap

- **Context:** Phone gallery failed when UFW blocked TCP 8765; users need in-app hints without guessing.
- **Decision:** `bootstrap/firewall.py` probes firewalld/UFW rules and a LAN TCP self-test; expose via `/api/server-info.firewall`. Shell helper `scripts/firewall/allow-spacemaker-port.sh` + task `firewall-allow`. Do not run MTP reconcile on every settings snapshot (blocks gallery clients).
- **Rationale:** Detection is best-effort but actionable; device scans stay on `/api/devices` only.

## 2026-09-22 — Gallery QR via segno (adapter-only)

- **Context:** Step 3 and LAN sharing need a scannable QR for `/gallery`; domain must stay free of QR libraries.
- **Decision:** Add `segno` as a runtime dependency; generate SVG at `GET /api/gallery/qr.svg` in the FastAPI adapter. Thumbnails lazy-generated under `{library}/.thumbnails/` via `SubprocessThumbnailGenerator` (ImageMagick / FFmpeg).
- **Rationale:** Keeps hexagonal boundaries; small dependency; EXIF dates via existing bundled ExifTool on `MediaProbePort.captured_at`.

## 2026-09-22 — Bundled CLIs + legal pack

- **Context:** User requires no manual third-party installs; privacy policy, third-party home pages, disclaimer in installer.
- **Decision:** All manifest tools bundled per OS/arch; `resolve_tool_path()` frozen vs dev. Docs in `docs/legal/`; spec `specs/legal/SPEC.md`; manifest YAML synced to `BundledTool` enum via tests.
- **Rationale:** Self-contained desktop product; transparency and liability coverage before public release.

## 2026-09-22 — Bundle adb per OS/arch

- **Context:** User wants ADB included in the final installer/binary, not a separate user install.
- **Decision:** Release builds ship Google platform-tools `adb` (and later libmtp) for each target OS/CPU; `AdbDeviceRepository` resolves bundled path first. PATH fallback only for dev/source runs. Spec: `specs/packaging/SPEC.md`.
- **Rationale:** Matches self-contained desktop app goal; adbutils still drives the client but must point at our binary.

## 2026-09-22 — Unified libmtp for MTP adapter

- **Context:** User asked whether Win/Linux users must install libmtp; OS already exposes MTP in Explorer/file managers.
- **Decision:** libmtp is the **application** MTP client on Windows, Linux, and macOS (one adapter path). User-facing copy: set phone to MTP only; do not tell Win/Linux users to install libmtp. Packaged app bundles libmtp tools when feasible.
- **Rationale:** Native OS MTP is for humans; SpaceMaker still needs libmtp (or equivalent) in code. Single stack beats WPD/gphoto2 split for v1.

## 2026-09-22 — MTP default, ADB recommended

- **Context:** User chose default extract path and platform tooling.
- **Decision:** Step 1 defaults to MTP; toggle to ADB (recommended) with info help. adbutils for ADB on all platforms.
- **Rationale:** Lower friction for casual users; ADB labeled recommended for speed/reliability when debugging is enabled.

## 2026-09-22 — uv quality gate and Biome for web

- **Context:** User requested srxy-style uv/ruff/ty checks plus JS lint for web UI.
- **Decision:** `pyproject.toml` + `uv run task checks` (`scripts/quality/checks.sh`: ruff, ty, pytest). Web: `package.json` + Biome 2.x on wireframes and future `static/` JS.
- **Rationale:** Matches Astral toolchain on Python; single fast linter/formatter for vanilla JS without separate ESLint+Prettier until needs grow.

## 2026-09-22 — Feature spec split

- **Context:** Step 2 SDD after wireframe approval.
- **Decision:** Four specs: `main-wizard`, `extract-media`, `convert-media`, `gallery` with cross-links; index at `specs/README.md`.
- **Rationale:** Matches hexagonal use cases and keeps convert policy testable in isolation.

## 2026-09-22 — SDD, wireframes, and test style

- **Context:** Greenfield SpaceMaker; user referenced GamesLibrary SDD and srxy tests.
- **Decision:** Markdown specs in `specs/<feature>/SPEC.md` (not Cucumber `.feature` files). Wireframes in `wireframes/` before specs. pytest with `test_given_…_when_…_then_…` naming and `# given` / `# when` / `# then` bodies (srxy style).
- **Rationale:** Matches existing agent workflows; keeps UX and behavior review separate; fast unit tests without Gherkin tooling.

## 2026-09-22 — Library folder layout and conversion outcomes

- **Context:** User refined conversion vs `convert_all_1_1.sh` with two-folder workflow extended to four outcomes.
- **Decision:** Library root contains `originals/`, `converted/`, `error/`, `invalid/`. Successful encode or move-as-is removes source from `originals/`. Failed encode: one retry, then `error/`. Unsupported/broken: `invalid/`. UI warnings with Review / Move-to-converted for errors.
- **Rationale:** Clear separation for gallery (`converted/` only), user review paths, and idempotent convert pipeline.

## 2026-09-22 — Compression reference

- **Context:** User's bash script encodes AVIF/AV1 rules, DNG+JPEG collision names, web-compat skip, size rollback.
- **Decision:** Vend `docs/reference/convert_all_1_1.sh` as authoritative compression reference; domain policy documented in `docs/playbooks/SpaceMaker-adaptations.md` and future specs.
- **Rationale:** Single repo-truth for FFmpeg/ImageMagick flags during spec and adapter implementation.
