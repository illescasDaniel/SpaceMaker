---
name: gallery-open-in-maps-revalidated-url
description: EXIF GPS is untrusted: the desktop bridge re-parses and rebuilds the Maps URL before opening it
type: decision
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

Open in Maps: desktop `js_api` bridge with server-side URL re-validation.

- **Context:** gallery item Location gets an "Open in Maps ↗" link (`specs/gallery-open-in-maps/SPEC.md`). GPS text is untrusted EXIF; pywebview may ignore `target=_blank`.
- **Decision:** the web client parses GPS strictly (`web/src/gps.ts`) and builds a Google Maps URL from validated numbers; on desktop, `DesktopApi.open_external_url` → `OpenMapLocation` use case re-parses and rebuilds the URL (`domain/map_link.py`) before `webbrowser.open`. No index/API/probe change.
- **Rationale:** keeps the Python side unchanged for data, and the bridge can never be used to open arbitrary URLs.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-02 — Open in Maps: desktop `js_api` bridge with server-side URL re-validation".
