_Last updated: 2026-09-24_

## Branch

`claude/qt-dependency-assessment-knsl0c`

## Current focus

Dropped Qt as a forced dependency on Windows/macOS — pywebview now uses each OS's
native backend there (WebView2 `edgechromium` on Windows, WKWebView `cocoa` on
macOS), no Qt bundling needed. Linux keeps Qt WebEngine (AppImage still pins a
known Chromium version instead of the host's `webkit2gtk`). See `memory/decisions.md`
("Native pywebview backend on Windows/macOS; Qt WebEngine kept Linux-only").

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
