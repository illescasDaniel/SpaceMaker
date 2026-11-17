---
name: windows-webengine-freeze-native-style
description: Windows WebEngine freeze/black-surface workarounds; native QtWidgets style
type: decision
date: 2026-09-24
status: current
supersedes:
superseded_by:
source:
---

Windows WebEngine freeze/black-surface fix attempts; QtWidgets native style (windows11/Fusion).

- **Context:** Windows dogfooding surfaced a Chromium-on-Windows GPU-compositor bug — the pywebview `QWebEngineView` surface freezes or renders black until the window is moved/resized (same bug class as Chrome/Discord on affected driver/GPU combos; matches open Qt bugs QTBUG-47753/51892/56674/57913). Separately, the user asked for native-looking dialogs (WinUI on Windows, native on macOS, Material on Linux) for pywebview's own dialogs.
- **Decision (freeze bug, `qt_webengine_gpu_flags.py`):** Two attempts ruled out and recorded in the module docstring so they aren't retried: `QTWEBENGINE_CHROMIUM_FLAGS=--use-angle=d3d9` broke rendering outright (EGL "Requested version is not supported", cascading "context lost" errors) — WebEngine's D3D11 RHI/shared-buffer compositor path requires a matching D3D11 ANGLE context. `QSG_RHI_BACKEND=opengl` had no effect at all, because this app's `QWebEngineView` is plain QtWidgets (via pywebview's Qt backend), not a QML `WebEngineView` inside a `QQuickWindow` — `QSG_RHI_BACKEND` only governs Qt Quick's own scenegraph, not how Chromium's GPU process picks its compositor backend for a QtWidgets view (that's `QTWEBENGINE_CHROMIUM_FLAGS`). A `vulkan` `QSG_RHI_BACKEND` value does exist on Windows (not Linux-only) but is irrelevant here for the same QtWidgets-vs-QML reason, and pairing it with a Chromium-side `--use-angle=vulkan` flag would be a less-tested combination than the d3d9 attempt that already broke rendering — declined. Current attempt: `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu-compositing`, which disables Chromium's out-of-process Viz display compositor (the DXGI-shared-buffer path also implicated in the separate `QDxgiVSyncService`/`QThreadStorage` shutdown warnings) while keeping GPU rasterization — less invasive than a full `--disable-gpu`. Pending user confirmation on Windows hardware (no GPU/display in the dev sandbox to verify).
- **Decision (native style, new `qt_native_style.py`):** `QT_QUICK_CONTROLS_STYLE` (raised during discussion) does not apply — there is no QML/Qt Quick Controls anywhere in this codebase, only QtWidgets (`QMessageBox` in `qt_webengine_shutdown.py`, `QFileDialog`-backed pickers via pywebview's `create_file_dialog()` in `desktop_api.py`); adopting QML app-wide just to theme two dialog call sites was considered out of scope. Applied via the same "wrap pywebview's `qt_platform.setup_app`" pattern as `install_qt_webengine_shutdown_fix()`: Windows gets `QStyleFactory.create("windows11")` (Qt 6.7+'s built-in WinUI-style approximation for widgets), Linux gets built-in `"Fusion"`, macOS is left alone (already native via `QMacStyle` by default). The third-party `qt-material` package was considered for a true Material Design widget look on Linux and declined by the user in favor of the dependency-free built-in Fusion style.
- **Rationale:** Recording the two dead-end env vars directly in the module docstring (not just here) so a future session reading the code doesn't re-try either one blind. The freeze-bug fix is unverified pending the user testing on real Windows hardware — this is a documented next experiment, not a confirmed fix.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Windows WebEngine freeze/black-surface fix attempts; QtWidgets native style (windows11/Fusion)".
