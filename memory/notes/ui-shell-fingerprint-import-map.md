---
name: ui-shell-fingerprint-import-map
description: shell version is an automatic hash of static/js; import map + clear HTTP cache on launch; no manual bumps
type: decision
date: 2026-09-29
status: current
supersedes: ui-shell-version-single-source
superseded_by:
source:
---

Drop manual shell-version bumps; fingerprint + import map + clear HTTP cache on launch.

- **Context:** User still saw gallery "Loading more…" after JS fixes and asked why we need shell versions — lightweight pages should always be latest, not cached. Diagnosis: HTML stamped `main.js?v=VERSION`, but relative ES imports (`import "./api.js"`) fetch unversioned URLs; Qt WebEngine reused stale module bytes despite `Cache-Control: no-store`. A stale `api.js` without `R.api` threw synchronously *after* the spinner was shown, and `.catch()` never ran — spinner stuck. Manual `UI_SHELL_VERSION` bumps were easy to forget and didn't fix relative imports anyway.
- **Decision:** (1) `UI_SHELL_VERSION` is now an auto SHA-256 prefix of `static/js/*.js` at process start (no hand edits). (2) `stamp_shell_html` emits an import map remapping every `/static/js/*.js` to `?v=<token>`, and also stamps shell CSS hrefs. (3) WebEngine profile slug is fixed `default` (stop proliferating versioned cache dirs). (4) Desktop launch clears HTTP/Code/GPU/Service Worker caches under that profile. (5) Gallery timeline fetch guards `typeof R.api` + try/catch so the spinner cannot stick on sync failures. Keep `no-store` on shell HTML/CSS/JS; keep long-lived cache only for `/media/` (and ETag revalidation for `/thumbs/`).
- **Rationale:** Matches the product rule "always open the latest UI" without agent ritual; import map closes the relative-import hole that versioned `main.js` alone could not; clearing Chromium HTTP cache on launch is cheap for this app and matches "we don't need a cache for lightweight pages."

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Drop manual shell-version bumps; fingerprint + import map + clear HTTP cache on launch".
