---
date: 2026-10-18
area: code
severity: blocked
status: fixed (url-field: execCommand first, uncommitted)
---

**Call:** Copy button using `navigator.clipboard.writeText` in the desktop webview (pywebview + QtWebEngine).
**Expected:** URL copied.
**Got:** `TypeError: setFeaturePermission(...) argument 3 has unexpected type 'int'` from `webview/platforms/qt.py: onFeaturePermissionRequested`; pywebview answers every non-media feature request with a plain int instead of `QWebEnginePage.PermissionPolicy`, so the permission is never resolved and the copy fails. Vitest/jsdom and the Browser pane cannot reproduce it; only the real Qt app can.
**Workaround:** use `document.execCommand("copy")` first (no permission request); `navigator.clipboard` only as a fallback.
**Idea:** avoid any web API that triggers a QtWebEngine feature permission (clipboard, notifications, geolocation) in the desktop shell, or patch/override `onFeaturePermissionRequested`.
