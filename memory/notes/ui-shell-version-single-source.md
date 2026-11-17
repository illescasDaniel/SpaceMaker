---
name: ui-shell-version-single-source
description: one UI_SHELL_VERSION constant stamped into HTML; silent one-shot reload instead of a banner
type: decision
date: 2026-09-27
status: superseded
supersedes:
superseded_by: ui-shell-fingerprint-import-map
source:
---

UI shell version: single source of truth + silent auto-reload (no mismatch banner).

- **Context:** Desktop showed "UI and server do not match" because `UI_SHELL_VERSION` in Python (`2026.09.transfer-files`) had drifted from a hardcoded `EXPECTED_UI_SHELL_VERSION` in `app.js` (`2026.09.gallery-nav`). The dual constant was easy for agents to forget when bumping the shell; the banner was a false positive even with a fresh, correct UI. User asked that opening SpaceMaker always get the latest UI and never surface that error.
- **Decision:** Keep one constant (`UI_SHELL_VERSION` in `ui_shell.py`). Serve desktop/mobile-gallery HTML through `stamp_shell_html()` so the page embeds `window.SPACEMAKER_UI_SHELL_VERSION` and `app.js?v=…` from that same value. Remove the JS expected-version constant. On a true stale WebEngine document, `healIfStaleShell` does a one-shot `location.replace` with a cache-bust query instead of showing a banner. Expand `Cache-Control: no-store` to all `/static/` paths (not only `app.js`).
- **Rationale:** Serve-time stamping makes page and `/api/settings` unable to disagree when both are live; auto-reload heals the only remaining case (cached HTML). Bumping shell assets is again one edit in one file.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — UI shell version: single source of truth + silent auto-reload (no mismatch banner)".

Superseded by [ui-shell-fingerprint-import-map](ui-shell-fingerprint-import-map.md).
