---
name: native-pywebview-win-mac
description: edgechromium on Windows, cocoa on macOS; Qt WebEngine only on Linux
type: decision
date: 2026-09-24
status: current
supersedes:
superseded_by:
source:
---

Native pywebview backend on Windows/macOS; Qt WebEngine kept Linux-only.

- **Context:** User asked why Qt was a dependency at all given pywebview is already the desktop shell, and whether it could be dropped to cut app size/overhead. Assessed: `--gui` defaulted to `qt` unconditionally on every OS, and `pyqt6`/`pyqt6-webengine`/`qtpy` were unconditional `pyproject.toml` dependencies, even though pywebview has native, dependency-free backends on Windows (`edgechromium`, WebView2, ships with Windows 10/11) and macOS (`cocoa`, WKWebView, built into the OS). Linux is the one platform where dropping Qt has a real cost: the Linux AppImage deliberately bundles Qt WebEngine (see the "Linux 1.0 release" entry below) specifically to pin a known Chromium version instead of depending on the host distro's `webkit2gtk`, so switching Linux to the `gtk` backend would reopen that exact problem.
- **Decision:** `desktop.py` gets `_default_gui_backend()`: `edgechromium` on `win32`, `cocoa` on `darwin`, `qt` otherwise (Linux); `--gui` still overrides for dev/testing. All Qt-only setup (`install_qt_webengine_gpu_flags`, `install_qt_webengine_shutdown_fix`, `install_qt_native_style`, `_apply_qt_window_icon`, `finalize_qt_after_webview`) is now gated on the resolved backend actually being `"qt"`, not just called unconditionally. `pyproject.toml` marks `pyqt6`, `pyqt6-webengine`, `qtpy` as `sys_platform == 'linux'`-only. `packaging/spacemaker.spec` (Windows/macOS PyInstaller onefile) now excludes whichever pywebview backends the build OS doesn't use (including `qt` itself on Windows/macOS), computed from `sys.platform` at spec-build time. Linux AppImage packaging (`prune_pyqt6.sh`, `build-appdir.sh`) is untouched. Added `tests/unit/test_desktop_gui_backend.py`.
- **Rationale:** Windows/macOS get a strictly smaller, simpler dependency set (no PyQt6/PyQt6-WebEngine wheels, no Qt/Chromium-compositor shutdown-teardown or GPU-flag workarounds to maintain) with no downside — WebView2/WKWebView are the natural choice on those OSes regardless of app size. Linux keeps Qt because the AppImage's whole point is a self-contained, version-pinned Chromium; trading that for a `webkit2gtk` dependency would just move the "which engine version do we get" problem onto the user's distro, which is what the existing AppImage decision was made to avoid. Not verified with a real Windows/macOS GUI session (no such hardware in this sandbox) — only import/dependency-resolution logic and the backend-selection function were tested; a real click-through on Windows/macOS is still pending, same caveat as the earlier Qt GPU-flag fix.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Native pywebview backend on Windows/macOS; Qt WebEngine kept Linux-only".
