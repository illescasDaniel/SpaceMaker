---
name: qt-smooth-wheel-scrolling
description: Chromium smooth scrolling enabled in Qt WebEngine; user-set flags kept
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

Enable Chromium smooth wheel scrolling in the Qt WebEngine desktop shell.

- **Context:** User noticed the desktop shell's wheel scrolling felt abrupt (line jumps) compared with Brave/Chrome. Web pages cannot control wheel-scroll physics (CSS `scroll-behavior` only affects programmatic/anchor scrolls; JS wheel-hijacking libraries break accessibility and hurt long gallery lists), but the desktop shell owns its engine. Qt WebEngine ships with Chromium's animated wheel scrolling off. User A/B-tested on Linux: `--enable-smooth-scrolling` alone felt closest to Brave; adding `--enable-features=WindowsScrollingPersonality` was not preferred.
- **Decision:** Rename `qt_webengine_gpu_flags.py` → `qt_webengine_chromium_flags.py` (`install_qt_webengine_chromium_flags`), which merges SpaceMaker's default flags into `QTWEBENGINE_CHROMIUM_FLAGS`: `--enable-smooth-scrolling` on every platform plus the existing Windows-only `--disable-gpu-compositing`. User-set flags are kept; a default is skipped when the user already set the same switch either way (e.g. `--disable-smooth-scrolling`). Previously `setdefault` meant any user-set value silently dropped the Windows GPU workaround. WebView2 (Windows default) and WKWebView (macOS) already scroll smoothly natively — untouched.
- **Rationale:** Matches mainstream-browser feel with a one-line engine flag instead of page-side scroll hijacking; merge semantics keep both the scroll flag and the GPU workaround composable with developer overrides.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Enable Chromium smooth wheel scrolling in the Qt WebEngine desktop shell".
