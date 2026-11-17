---
name: system-theme-self-hosted-fa
description: one theme.css with prefers-color-scheme; vendored Font Awesome (CSP font-src self)
type: decision
date: 2026-09-23
status: current
supersedes:
superseded_by:
source:
---

System theme and self-hosted Font Awesome for gallery nav.

- **Context:** Per-module light vs dark palettes diverged from user expectation; gallery prev/next used hard-coded dark overlays with poor contrast in light mode; chevron alignment was off with absolute positioning.
- **Decision:** Single `theme.css` with `prefers-color-scheme` for all shells; remove `syncShellTheme` / gallery-system-theme overrides. Gallery nav uses CSS grid overlay + vendored Font Awesome Free solid chevrons under `static/vendor/fontawesome/` (CSP `font-src 'self'`).
- **Rationale:** Matches OS appearance everywhere; keeps LAN/desktop offline-capable without CDN; grid `align-self: center` tracks preview height reliably.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — System theme and self-hosted Font Awesome for gallery nav".
