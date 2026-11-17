---
name: gallery-item-delete-web-share
description: gallery item delete; desktop opens files with the OS instead of raw Download/Share
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

Gallery item delete and Web Share export.

- **Context:** Item page needed host path visibility, safe removal from `converted/`, and phone-friendly sharing without manual download steps.
- **Decision:** `GetGalleryItem` returns `absolute_path`; `DeleteGalleryItem` + `DELETE /api/gallery/item`. Desktop uses `POST /api/gallery/open` (xdg-open / OS reveal) instead of raw Download/Share; phone shell keeps Download + friendly export only. Stub `GET /json/version` for Chromium probe noise. HTML shells use default caching (no forced no-cache).
- **Rationale:** Shell-specific markup; host actions on PC only; avoid uvicorn 404 spam without hurting reload performance in production.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Gallery item delete and Web Share export".
