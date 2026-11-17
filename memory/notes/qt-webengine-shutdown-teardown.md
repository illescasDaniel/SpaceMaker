---
name: qt-webengine-shutdown-teardown
description: idempotent WebEngine teardown and a finalize pass after pywebview's loop exits
type: decision
date: 2026-09-24
status: current
supersedes:
superseded_by:
source:
---

Qt WebEngine shutdown teardown hardened further for Windows.

- **Context:** The existing `install_qt_webengine_shutdown_fix()` (page/profile `deleteLater` + a short `processEvents` drain) was tuned on Linux; on Windows it still left the process hanging or crashing on quit because WebChannel/nav-handler objects, top-level widgets, and the URL request interceptor were never explicitly torn down, and Windows needs longer event-drain rounds plus real `time.sleep` gaps for `QDxgiVSyncService` to unwind asynchronously.
- **Decision:** `_tear_down_webview` is now idempotent (`_spacemaker_webengine_torn_down` guard) and additionally disconnects webchannel/nav-handler/cookie-store signals, tears down the request interceptor, and deletes top-level widgets; new `finalize_qt_after_webview()` runs after pywebview's own event loop exits (called from `desktop.py` `main()` before `_shutdown_services` and `os._exit(0)`). Round/delay counts are platform-tuned via `_shutdown_event_rounds()` / `_shutdown_quit_delay_ms()` / `_shutdown_finalize_passes()` (higher on `win32`).
- **Rationale:** `os._exit(0)` was already accepted as the pragmatic hard-exit (uvicorn's daemon thread can't be joined without a bigger refactor); this change reduces how much unclean Chromium/Qt state that hard exit has to paper over, rather than replacing it.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Qt WebEngine shutdown teardown hardened further for Windows".
