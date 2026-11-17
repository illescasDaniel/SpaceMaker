---
name: qt-shutdown-warnings-not-pursued
description: QDxgiVSyncService/QThreadStorage warnings judged benign and not pursued
type: decision
date: 2026-09-24
status: superseded
supersedes:
superseded_by: qt-shutdown-warnings-log-filter
source:
---

`QDxgiVSyncService`/`QThreadStorage` shutdown warnings: confirmed benign, confirmed unrelated to the WebEngine freeze fix, not pursuing further.

- **Context:** User asked whether `QDxgiVSyncService not destroyed in time` / `QThreadStorage: entry N destroyed before end of thread` (seen at desktop app shutdown on Windows) is a known Qt issue with a proper fix, separately from the WebEngine freeze bug (`--disable-gpu-compositing`, previous entries) and the shutdown-teardown hardening already in `qt_webengine_shutdown.py` (see the "hardened further for Windows" entry above). After the freeze fix landed and was confirmed working, the user re-tested and these two lines still appear at shutdown.
- **Finding:** Qt's own blog post on WebEngine's graphics integration (https://www.qt.io/blog/new-graphics-integration-in-qt-webengine-6.6-and-even-6.5.1) confirms Qt WebEngine >=6.5.1 moved Windows to a D3D11 RHI backend that shares GPU buffers with Chromium's compositor over DXGI — `QDxgiVSyncService` is part of that DXGI-backed presentation path, and it tears down **asynchronously**, after the last native window is destroyed. `qt_webengine_shutdown.py`'s `finalize_qt_after_webview()` already gives Windows extra event-drain rounds and a `time.sleep(0.2)` specifically to let it unwind, but that's a bounded best-effort wait racing against `desktop.py`'s subsequent `os._exit(0)` hard exit (accepted as pragmatic since uvicorn's daemon thread can't be joined cleanly — see that same earlier entry). `QThreadStorage`'s "entry destroyed before end of thread" warning is Qt's own generic shutdown-ordering log line, not specific to WebEngine; both are shutdown-path warnings, not runtime errors, and the process still exits (no hang, no non-zero exit reported).
- **Ruled out:** `--disable-gpu-compositing` (the fix that resolved the separate freeze/black-surface bug) does **not** eliminate these warnings — confirmed by direct user retest. This shows the freeze bug and this shutdown warning, despite both touching the same DXGI-backed compositor plumbing, are not the same failure and don't share a fix; disabling Viz's out-of-process compositor doesn't stop `QDxgiVSyncService` itself from existing or from tearing down asynchronously.
- **Decision:** Not pursuing this further. It's cosmetic log output on the way out the door, not a functional bug — the only remaining lever (increasing `_shutdown_finalize_passes()`/sleep durations even more in `qt_webengine_shutdown.py`) would only trade a slower quit for maybe-quieter logs, with no guarantee, since the teardown timing is Qt/Chromium-internal and not something this app controls. If it starts being reported as more than log noise (a hang, a crash, a non-zero exit code), reopen and re-investigate from there — otherwise leave `qt_webengine_shutdown.py` as-is.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — `QDxgiVSyncService`/`QThreadStorage` shutdown warnings: confirmed benign, confirmed unrelated to the WebEngine freeze fix, not pursuing further".

Superseded by [qt-shutdown-warnings-log-filter](qt-shutdown-warnings-log-filter.md).
