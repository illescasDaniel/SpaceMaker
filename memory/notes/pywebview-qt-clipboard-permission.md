---
name: pywebview-qt-clipboard-permission
description: navigator.clipboard fails in the pywebview Qt shell (feature-permission TypeError); use execCommand first
type: gotcha
date: 2026-10-18
status: current
supersedes:
superseded_by:
source:
---

In the desktop shell (pywebview + QtWebEngine) `navigator.clipboard.writeText` fails: pywebview answers feature-permission requests with a plain int instead of `QWebEnginePage.PermissionPolicy` (`TypeError: setFeaturePermission(...) argument 3 has unexpected type 'int'`), so the permission never resolves. Vitest/jsdom and the browser pane cannot reproduce it; only the real Qt app does.

**How to apply:** copy with `document.execCommand("copy")` first and use `navigator.clipboard` only as a fallback (done in `web/src/url-field.ts` and `web/src/dom.ts`, confirmed at HEAD 2026-11-17); avoid other web APIs that trigger QtWebEngine feature permissions (notifications, geolocation).

Source: `memory/friction/2026-10-18-pywebview-qt-clipboard-permission.md`.
