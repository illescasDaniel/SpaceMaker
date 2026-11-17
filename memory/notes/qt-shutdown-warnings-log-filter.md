---
name: qt-shutdown-warnings-log-filter
description: benign Qt shutdown warnings filtered from logs; teardown timing left alone
type: decision
date: 2026-09-24
status: current
supersedes: qt-shutdown-warnings-not-pursued
superseded_by:
source:
---

`QDxgiVSyncService`/`QThreadStorage` shutdown warnings: narrowed the earlier "not pursuing further" decision to a log filter, since the actual ask was noise, not the race.

- **Context:** User re-reported the same two lines from the entry below. Confirmed on questioning: still just console noise on exit, no hang/crash/non-zero exit — i.e. exactly the "otherwise leave `qt_webengine_shutdown.py` as-is" branch of that decision. The narrower ask was to stop the lines from printing, not to chase the underlying async DXGI-teardown race further.
- **Decision:** Did **not** touch `finalize_qt_after_webview()`, `finish_quit()`, or any of the existing drain-round/sleep timing — that logic is confirmed to already prevent real hangs/crashes and tuning it further was already ruled out as not worth it. Instead added `_is_benign_shutdown_warning()` and `install_benign_shutdown_warning_filter()` to `qt_webengine_shutdown.py`: a `QtCore.qInstallMessageHandler` wrapper that drops only messages starting with `"QDxgiVSyncService not destroyed in time"` or `"QThreadStorage: entry"`, forwarding everything else (including other warnings) to whatever handler was previously installed. Wired in from `install_qt_webengine_shutdown_fix()`, active for the app's full lifetime (no need to uninstall — the process ends via `os._exit(0)` shortly after). Confirmed via `qtpy`/PySide6 that `qInstallMessageHandler(None)` returns the previously-installed handler (or `None` for Qt's default), which the wrapper falls back to a plain `sys.stderr.write` for. User confirmed on a real run that the window still closes promptly and the two lines no longer appear.
- **Rationale:** Both messages are genuine Qt (qtbase) internal `qWarning()`-style log lines — not raw Chromium subprocess stderr — so `qInstallMessageHandler` is the correct, minimal-risk mechanism (as opposed to wrapping `sys.stderr`, which would also risk swallowing output from an unrelated child process). Matching by message-text prefix rather than log level/category keeps the filter narrow: only these two known-benign lines are suppressed, every other Qt warning still reaches the console exactly as before.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — `QDxgiVSyncService`/`QThreadStorage` shutdown warnings: narrowed the earlier "not pursuing further" decision to a log filter, since the actual ask was noise, not the race".
