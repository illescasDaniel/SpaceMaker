# Technical decisions

Append-only log (newest first). Never rewrite history.

## 2026-09-24 — `QDxgiVSyncService`/`QThreadStorage` shutdown warnings: confirmed benign, confirmed unrelated to the WebEngine freeze fix, not pursuing further

- **Context:** User asked whether `QDxgiVSyncService not destroyed in time` / `QThreadStorage: entry N destroyed before end of thread` (seen at desktop app shutdown on Windows) is a known Qt issue with a proper fix, separately from the WebEngine freeze bug (`--disable-gpu-compositing`, previous entries) and the shutdown-teardown hardening already in `qt_webengine_shutdown.py` (see the "hardened further for Windows" entry above). After the freeze fix landed and was confirmed working, the user re-tested and these two lines still appear at shutdown.
- **Finding:** Qt's own blog post on WebEngine's graphics integration (https://www.qt.io/blog/new-graphics-integration-in-qt-webengine-6.6-and-even-6.5.1) confirms Qt WebEngine >=6.5.1 moved Windows to a D3D11 RHI backend that shares GPU buffers with Chromium's compositor over DXGI — `QDxgiVSyncService` is part of that DXGI-backed presentation path, and it tears down **asynchronously**, after the last native window is destroyed. `qt_webengine_shutdown.py`'s `finalize_qt_after_webview()` already gives Windows extra event-drain rounds and a `time.sleep(0.2)` specifically to let it unwind, but that's a bounded best-effort wait racing against `desktop.py`'s subsequent `os._exit(0)` hard exit (accepted as pragmatic since uvicorn's daemon thread can't be joined cleanly — see that same earlier entry). `QThreadStorage`'s "entry destroyed before end of thread" warning is Qt's own generic shutdown-ordering log line, not specific to WebEngine; both are shutdown-path warnings, not runtime errors, and the process still exits (no hang, no non-zero exit reported).
- **Ruled out:** `--disable-gpu-compositing` (the fix that resolved the separate freeze/black-surface bug) does **not** eliminate these warnings — confirmed by direct user retest. This shows the freeze bug and this shutdown warning, despite both touching the same DXGI-backed compositor plumbing, are not the same failure and don't share a fix; disabling Viz's out-of-process compositor doesn't stop `QDxgiVSyncService` itself from existing or from tearing down asynchronously.
- **Decision:** Not pursuing this further. It's cosmetic log output on the way out the door, not a functional bug — the only remaining lever (increasing `_shutdown_finalize_passes()`/sleep durations even more in `qt_webengine_shutdown.py`) would only trade a slower quit for maybe-quieter logs, with no guarantee, since the teardown timing is Qt/Chromium-internal and not something this app controls. If it starts being reported as more than log noise (a hang, a crash, a non-zero exit code), reopen and re-investigate from there — otherwise leave `qt_webengine_shutdown.py` as-is.

## 2026-09-24 — Fixed the SelectorEventLoop fix itself: uvicorn's custom `loop=` string must resolve to the loop class directly, not a factory function; added a real-process smoke test

- **Context:** The previous entry's `event_loop.py` fix (`uvicorn.run(..., loop=uvicorn_loop_for_platform())` pointing a `"module:attr"` string at a `windows_selector_loop_factory()` function that returned `asyncio.SelectorEventLoop`) looked correct and passed all existing tests, but broke the app outright on the user's Windows machine — the server thread died instantly with `TypeError: BaseEventLoop.create_task() missing 1 required positional argument: 'coro'` and cascading "missing 1 required positional argument: 'self'" errors during shutdown. Reproduced locally with `uv run spacemaker --server-only` and bisected via `git stash`.
- **Root cause:** `uvicorn.config.Config.get_loop_factory()` only calls the resolved factory with `use_subprocess=...` for names in its `LOOP_FACTORIES` table (`"none"`/`"auto"`/`"asyncio"`/`"uvloop"`/`"zuvloop"`). For any other string (a custom `"module:attr"` path), it does `return import_from_string(self.loop)` and uses the resolved object **directly** as the final zero-arg factory `asyncio.Runner` calls — it does not call it a second time to unwrap a "factory of factories" the way the built-in `asyncio_loop_factory`/`uvloop_loop_factory` functions work. My function matched the shape of those built-ins (returning the *class*, expecting one more call) but was being used as a *custom* string, which skips that extra call — so `asyncio.Runner._loop` ended up holding the un-instantiated `SelectorEventLoop` class itself, and every subsequent method call on it (`create_task`, `shutdown_asyncgens`, `close`) failed as an unbound-method call.
- **Decision:** `uvicorn_loop_for_platform()` now returns the string `"asyncio:SelectorEventLoop"` directly (pointing straight at the stdlib class) instead of a wrapper function — no custom factory function needed at all. Verified via a standalone script that `uvicorn.Config(loop="asyncio:SelectorEventLoop").get_loop_factory()` resolves to the class and instantiates a working `_WindowsSelectorEventLoop`, then confirmed `uv run spacemaker --server-only` boots and serves a real request. Added `tests/integration/test_server_smoke.py` (new `smoke`-style integration test, and new `uv run task smoke` shortcut) that launches the actual `python -m spacemaker --server-only` process and polls a real endpoint — confirmed it reproduces this exact crash (full traceback dumped in the assertion message) when the previous broken function-based approach is reintroduced, and passes against the fix.
- **Rationale:** This bug was invisible to every existing test because they all use FastAPI's `TestClient` (in-process, no real `uvicorn.run()`/event-loop wiring at all) — only a test that boots the real OS process would catch it, which is exactly the gap the user asked to close ("create a proper smoke test... so that we run that smoke test the next time"). `tests/integration/test_server_smoke.py` runs as part of the normal `tests/integration` collection (`uv run task checks`), so it's not something that has to be remembered to run separately.

## 2026-09-24 — Windows ProactorEventLoop ConnectionResetError noise: switched uvicorn to SelectorEventLoop via `loop=` factory, not the deprecated asyncio policy API

- **Context:** After confirming `--disable-gpu-compositing` fixed the WebEngine freeze (see the entry below), the user hit a different Windows-only traceback: `Exception in callback _ProactorBasePipeTransport._call_connection_lost()` / `ConnectionResetError: [WinError 10054]`, logged when a LAN client (phone) reset the TCP connection mid-request (e.g. polling `/api/upload/session`) — a long-standing, still-open CPython stdlib bug in `ProactorEventLoop` (https://github.com/python/cpython/issues/149388, bpo-38856), cosmetic (the request had already returned 200 OK), not a crash.
- **Decision:** New `src/spacemaker/bootstrap/event_loop.py`: `uvicorn_loop_for_platform()` returns uvicorn's default `"auto"` loop string everywhere except win32, where it returns a `"module:attr"` string pointing at `windows_selector_loop_factory()` (mirrors the shape of uvicorn's own `uvicorn.loops.asyncio.asyncio_loop_factory`, returns `asyncio.SelectorEventLoop`). Wired into `desktop.py`'s `run_server()` via `uvicorn.run(..., loop=uvicorn_loop_for_platform())`. Confirmed via a standalone script that `uvicorn.config.Config(loop=<that string>).get_loop_factory()` resolves to `asyncio.SelectorEventLoop` and instantiates `_WindowsSelectorEventLoop`. Verified no `asyncio` subprocess/pipe usage anywhere in `src/` (only blocking `subprocess.run`/`Popen`), so SelectorEventLoop's lack of Proactor-only capabilities doesn't matter here.
- **Rationale:** The obvious fix, `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`, is deprecated as of Python 3.14 (removal in 3.16, confirmed via `ty check` warnings on this dev machine's 3.14.6 interpreter) — used uvicorn's own supported `loop=` customization point instead, which resolves via `uvicorn.importer.import_from_string` and is the documented way to hand uvicorn a non-default loop factory.

## 2026-09-24 — Windows WebEngine freeze/black-surface fix attempts; QtWidgets native style (windows11/Fusion)
## 2026-09-24 — Windows WebEngine freeze/black-surface fix attempts; QtWidgets native style (windows11/Fusion)

- **Context:** Windows dogfooding surfaced a Chromium-on-Windows GPU-compositor bug — the pywebview `QWebEngineView` surface freezes or renders black until the window is moved/resized (same bug class as Chrome/Discord on affected driver/GPU combos; matches open Qt bugs QTBUG-47753/51892/56674/57913). Separately, the user asked for native-looking dialogs (WinUI on Windows, native on macOS, Material on Linux) for pywebview's own dialogs.
- **Decision (freeze bug, `qt_webengine_gpu_flags.py`):** Two attempts ruled out and recorded in the module docstring so they aren't retried: `QTWEBENGINE_CHROMIUM_FLAGS=--use-angle=d3d9` broke rendering outright (EGL "Requested version is not supported", cascading "context lost" errors) — WebEngine's D3D11 RHI/shared-buffer compositor path requires a matching D3D11 ANGLE context. `QSG_RHI_BACKEND=opengl` had no effect at all, because this app's `QWebEngineView` is plain QtWidgets (via pywebview's Qt backend), not a QML `WebEngineView` inside a `QQuickWindow` — `QSG_RHI_BACKEND` only governs Qt Quick's own scenegraph, not how Chromium's GPU process picks its compositor backend for a QtWidgets view (that's `QTWEBENGINE_CHROMIUM_FLAGS`). A `vulkan` `QSG_RHI_BACKEND` value does exist on Windows (not Linux-only) but is irrelevant here for the same QtWidgets-vs-QML reason, and pairing it with a Chromium-side `--use-angle=vulkan` flag would be a less-tested combination than the d3d9 attempt that already broke rendering — declined. Current attempt: `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu-compositing`, which disables Chromium's out-of-process Viz display compositor (the DXGI-shared-buffer path also implicated in the separate `QDxgiVSyncService`/`QThreadStorage` shutdown warnings) while keeping GPU rasterization — less invasive than a full `--disable-gpu`. Pending user confirmation on Windows hardware (no GPU/display in the dev sandbox to verify).
- **Decision (native style, new `qt_native_style.py`):** `QT_QUICK_CONTROLS_STYLE` (raised during discussion) does not apply — there is no QML/Qt Quick Controls anywhere in this codebase, only QtWidgets (`QMessageBox` in `qt_webengine_shutdown.py`, `QFileDialog`-backed pickers via pywebview's `create_file_dialog()` in `desktop_api.py`); adopting QML app-wide just to theme two dialog call sites was considered out of scope. Applied via the same "wrap pywebview's `qt_platform.setup_app`" pattern as `install_qt_webengine_shutdown_fix()`: Windows gets `QStyleFactory.create("windows11")` (Qt 6.7+'s built-in WinUI-style approximation for widgets), Linux gets built-in `"Fusion"`, macOS is left alone (already native via `QMacStyle` by default). The third-party `qt-material` package was considered for a true Material Design widget look on Linux and declined by the user in favor of the dependency-free built-in Fusion style.
- **Rationale:** Recording the two dead-end env vars directly in the module docstring (not just here) so a future session reading the code doesn't re-try either one blind. The freeze-bug fix is unverified pending the user testing on real Windows hardware — this is a documented next experiment, not a confirmed fix.

## 2026-09-24 — `.claude/rules/` mirrors `.cursor/rules/`: hand-maintained copies, not symlinks

- **Context:** Claude Code shipped a new `.claude/rules/` feature (analogous to Cursor's `.cursor/rules/`). Tried the same symlink pattern already used for `.claude/skills -> ../.cursor/skills` (a directory symlink): first a blind directory symlink (rejected on inspection — Claude Code's docs say discovery is by literal `.md` extension, and every Cursor rule file is `.mdc`), then per-file symlinks named `<name>.md` pointing at the real `<name>.mdc` targets (valid on disk, content read correctly via `cat`/`Read`, but two independent tests — a fresh subagent probing for a phrase unique to one rule file, and the user's own `/context` in a genuinely fresh session — both showed **zero** `.claude/rules/` files loaded, only `AGENTS.md` under **Memory files**). Rewrote as five native `.claude/rules/*.md` files with plain-markdown content (no frontmatter — Claude Code only reads a `paths` field and ignores everything else, so omitting it entirely gives the same "always loaded" behavior as Cursor's `alwaysApply: true`). Re-tested with the user's own `/context`: all five now appear under **Memory files**.
- **Decision:** `.claude/rules/*.md` are hand-maintained duplicates of `.cursor/rules/*.mdc`, not symlinks or generated copies. Documented the dual-maintenance requirement directly in `AGENTS.md` ("Rules — Cursor vs Claude Code" section): edit both copies together, a mismatch is a bug.
- **Rationale:** The symlink approach that worked for `.claude/skills` doesn't generalize to `.claude/rules/` because skills discovery apparently tolerates (or doesn't care about) the underlying file extension the way rules discovery does — or possibly this specific desktop-app session type just doesn't implement `.claude/rules/` symlink-following at all (untested: whether a real standalone `claude` CLI session would resolve the symlink where this environment didn't). Rather than keep guessing at environment-specific symlink behavior, hand-maintained copies are unambiguous, verified working, and the five files are small enough that manual sync isn't a meaningful burden. A follow-up subagent test for the *native* `.md` files (no symlink involved) also came back negative before the user's own fresh-session `/context` confirmed they load — meaning a spawned subagent in this environment does **not** reliably reflect what a genuine new top-level session loads; don't trust subagent self-report for this class of question again, use `/context` in an actual fresh session instead.

## 2026-09-24 — Graphify feedback loop (`save-result`/`reflect`) adopted; `diagnose multigraph` documented as trigger-based, not routine

- **Context:** Walked through Graphify's less-obvious CLI surface (`diagnose multigraph`, `save-result`, `reflect`) on request, to decide whether they're worth using and, if so, to write that into `AGENTS.md` so future sessions pick it up without being re-asked.
- **Decision:** (1) `graphify diagnose multigraph` is documented as a trigger-based check (after a big refactor, or when a graph query result looks suspicious), not a per-task step — ran once against the live graph as a baseline: 0 collapsed edges, 0 dangling endpoints. (2) The `save-result`/`reflect` feedback loop is adopted: after a graph query that actually informed a real decision, tag its outcome (`useful`/`dead_end`/`corrected`); `reflect` deterministically aggregates tags into `graphify-out/reflections/LESSONS.md`. (3) `.gitignore` now un-ignores `graphify-out/memory/*.md` and `graphify-out/reflections/LESSONS.md` (previously blanket-ignored under `graphify-out/*`) so this signal persists across sessions/branches instead of resetting per clone/worktree, mirroring how `graph.json`/`GRAPH_REPORT.md` are already tracked.
- **Rationale:** No LLM cost — `save-result`/`reflect` are pure bookkeeping over outcomes I tag myself, so the marginal cost of adopting it is just discipline, not tokens or an API key. Untracked (gitignored) would have meant the accumulating "which graph nodes are actually reliable" signal lived only on one machine and vanished on every fresh clone, defeating the point of a cross-session feedback loop — same reasoning that already justifies tracking `memory/decisions.md` itself. `LESSONS.md` is explicitly *not* a replacement for `decisions.md`: it's auto-generated per-symbol reliability signal, not a hand-written per-decision narrative — both stay, documented side by side in `AGENTS.md`.

## 2026-09-24 — `.claude/skills` symlink: relative target, and `New-Item` directory-symlink pitfall

- **Context:** Following up on the previous session's `.claude/skills` symlink (see the `2026-09-24 — Claude Code project-skill discovery` entry below), the tracked blob content was found to be the literal absolute path `C:/Users/kaumi/Documents/Projects/SpaceMaker/.cursor/skills` — baked to this machine's username and clone location, so it would dangle on any other Windows machine and on Linux/macOS. Separately, recreating the symlink by hand with `New-Item -ItemType SymbolicLink -Path .claude\skills -Target ..\.cursor\skills` produced a **file**-type reparse point (`PSIsContainer: False`, `Attributes: Archive, ReparsePoint`) even though the target is a directory — so native Windows tools (`cd`, Explorer) couldn't traverse it, while Git Bash's `ls`/`cd` (POSIX emulation, ignores the NTFS file/dir reparse subtype) worked fine and masked the bug.
- **Decision:** Repointed the symlink to the relative target `../.cursor/skills` (commit `87b2196`). When the symlink needs manual recreation on Windows, use `mklink /D skills ..\.cursor\skills` (run from inside `.claude/`, via `cmd /c`) — not `New-Item -ItemType SymbolicLink`, which mistyped the reparse point even with a valid, existing directory target. Verified `git checkout` itself always creates the correct `Directory` reparse point (confirmed via a throwaway `git worktree add --detach` at a different path — `PSIsContainer: True`), so this pitfall only affects manual recreation, not clones/checkouts by git or other users.
- **Rationale:** A relative symlink target is required for the link to resolve on any machine/OS; `mklink /D` is the reliable manual-recreation path on Windows since `New-Item`'s directory detection for symlinks is unreliable, at least with relative targets.

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
