_Last updated: 2026-09-25_

## Branch

`claude/qt-dependency-assessment-knsl0c`

## Current focus

User is now testing this branch on real Windows hardware. Fixed a live crash they hit:
`reveal_in_file_manager` (`src/spacemaker/adapters/outbound/host/open_paths.py`) used
`subprocess.run(["explorer", "/select,", ...], check=True)`, but `explorer.exe`
routinely exits 1 even when it successfully opens Explorer with the file selected —
`check=True` turned that into a 500 from `POST /api/gallery/open`. Changed to
`check=False`; no test coverage change needed (this is a return-code-reliability fix,
not new behavior).

Second user-reported bug, now fixed: multi-file Photo Backup uploads (e.g. a folder
from Android) saved all files but converted only one — the rest sat unconverted
until the user left and re-entered Photo Backup. Two real code defects, both in
`src/spacemaker/bootstrap/services.py`:

1. `_run_convert`'s "more files arrived mid-conversion" requeue tried to call
   `self.start_convert(...)` recursively from inside the very function running as
   `self._convert_future`'s target — `_convert_job_active()` sees that future as
   not-done and blocks the requeue, silently no-opping it. Fixed by turning the
   recursive call into an in-place `while True` drain loop inside `_run_convert`
   itself (same thread/future, so no reentrancy).
2. Progress display reset to "0/1" each drain pass instead of showing one running
   total (e.g. "0/2" → "1/2" → "2/2"), because each drain pass re-scans
   `originals/` and reports its own local `(completed, total)`. Fixed by tracking
   `cumulative_completed` across passes and offsetting each pass's `on_progress`
   callback by it.
3. Root cause of why a pass ever needed the drain loop in the first place:
   `handle_wifi_upload` (called once per file from `/api/upload`'s per-file loop
   in `src/spacemaker/adapters/inbound/web/app.py`) called the convert-trigger
   after *every single file*, so with N files in one upload batch the convert job
   often started after only the first file had landed on disk, with total=1 baked
   in from the start. Fixed by renaming `_maybe_start_convert_drain` to public
   `maybe_start_convert_drain` and calling it once per request (in a `finally`
   around the file loop, so it still fires on partial failure) instead of once per
   file — so the initial total reflects the whole batch.

Verified: `uv run ruff check` clean on both touched files; `uv run pytest
--ignore=tests/unit/test_qt_webengine_shutdown.py` — 179 passed, 5 pre-existing
skips (POSIX-only tests). No test currently exercises the multi-file upload +
convert-progress path end-to-end — worth adding if this area gets touched again.
Awaiting the user's re-test on real Windows/Android hardware to confirm the
progress bar now reads 0/2 → 1/2 → 2/2 for a 2-photo batch.

Earlier in this branch: dropped Qt as a forced dependency on Windows/macOS —
pywebview now uses each OS's native backend there (WebView2 `edgechromium` on
Windows, WKWebView `cocoa` on macOS), no Qt bundling needed. Linux keeps Qt
WebEngine (AppImage still pins a known Chromium version instead of the host's
`webkit2gtk`). See `memory/decisions.md` ("Native pywebview backend on
Windows/macOS; Qt WebEngine kept Linux-only").

- `src/spacemaker/desktop.py`: new `_default_gui_backend()` (edgechromium/cocoa/qt
  per `sys.platform`); `--gui` still overrides. Qt-only setup
  (`install_qt_webengine_gpu_flags`, `install_qt_webengine_shutdown_fix`,
  `install_qt_native_style`, `_apply_qt_window_icon`, `finalize_qt_after_webview`)
  now gated on the resolved backend being `"qt"`.
- `pyproject.toml`: `pyqt6`/`pyqt6-webengine`/`qtpy` marked `sys_platform == 'linux'`.
- `packaging/spacemaker.spec`: excludes whichever pywebview backends the build OS
  doesn't use (including `qt` itself off Linux), computed from `sys.platform`.
- Docs updated: `specs/packaging/SPEC.md`, `docs/playbooks/SpaceMaker-adaptations.md`,
  `packaging/README.md`.
- New `tests/unit/test_desktop_gui_backend.py`.
- Verified: `uv run task checks` — ruff/ty green, full pytest green except one
  pre-existing, unrelated failure (`test_raw_image_convert.py`'s DNG-preview-fallback
  test, confirmed failing identically on the pre-change commit too — sandbox lacks a
  real ImageMagick/RAW toolchain, not caused by this change). `web` check fails only
  on missing `node_modules` (pre-existing, unrelated). Smoke-tested `desktop.main()`
  in `--server-only` mode (real uvicorn process, real HTTP 200) — no real Windows/macOS
  GUI hardware in this sandbox, so the actual WebView2/WKWebView window creation is
  unverified; flagged to the user as pending real-hardware confirmation, same as the
  earlier Qt GPU-flag fix.

## Next steps (this thread)

- Awaiting user confirmation on real Windows/macOS hardware that `edgechromium`/`cocoa`
  windows actually open correctly (this sandbox has no GUI to test).
- If confirmed, consider deleting the now-mostly-dead-on-Windows workaround code in
  `qt_webengine_gpu_flags.py`/`qt_webengine_shutdown.py`'s Windows-tuned paths — held
  off per this session's own earlier caution (only reproducible on real Windows/Qt,
  and WebView2 not proven bug-free until tested).

## Run

```bash
uv run task spacemaker
uv run task checks                  # ruff + ty + pytest, works natively on Windows
uv run task smoke                   # real-process server smoke test (subset of checks)
```

## Notes for Claude Code specifically (this machine)

- Project skills live at `.cursor/skills/` (Cursor's convention); Claude Code only
  auto-discovers `.claude/skills/`. Fixed via a real OS symlink
  `.claude/skills -> ../.cursor/skills` (relative target, portable across
  machines/OS). `git checkout` recreates it correctly on any clone.
- Older finished threads: `memory/archive.md` and `docs/agent-tooling.md`.
