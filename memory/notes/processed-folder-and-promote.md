---
name: processed-folder-and-promote
description: converted/ renamed processed/ (migrated on ensure); Compress off promotes originals as-is
type: decision
date: 2026-09-27
status: current
supersedes: library-folder-layout
superseded_by:
source:
---

Promote uncompressed media; `converted/` → `processed/`; Settings chrome.

- **Context:** With Compress media off, Wi‑Fi uploads stayed in `originals/` while Gallery indexed only `converted/`, so photos never appeared. User also wanted the gallery bucket renamed to `processed/`, a sticky header with Home|Gallery|Settings, and a Settings menu (clear prefs, full library reset, tools, legal last).
- **Decision:** (1) `LibraryFolder.PROCESSED = "processed"` with on-ensure migration from legacy `converted/`. (2) Easy drain: when compress off, `PromoteOriginalsToProcessed` move-as-is then sync gallery; when on, existing convert drain. (3) Ports/use cases `clear()` preferences + `ResetLibrary` (all buckets + `.thumbnails`/`.exports`/`.index.sqlite`); APIs `POST /api/preferences/clear` and `POST /api/library/reset`. (4) Sticky `.top-bar` + scrollable `.app-main`; no floating footer; default window 1152×864. (5) `spacemaker_data_dir` honors `SPACEMAKER_TOOLS_DIR` parent so prefs isolate in tests.
- **Rationale:** Gallery stays single-bucket (`processed/`); compress-off is still “no re-encode” but visible; Settings consolidates destructive/legal/tools entry points.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — Promote uncompressed media; `converted/` → `processed/`; Settings chrome".
