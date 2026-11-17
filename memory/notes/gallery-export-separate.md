---
name: gallery-export-separate
description: on-demand friendly export (JPEG q95, H.264 CRF 18) cached in .exports/, separate from library convert
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

Gallery export separate from library convert.

- **Context:** Users need Download-as-JPEG/MP4 on the item page without changing AVIF/AV1 library policy or size rollback.
- **Decision:** On-demand `ExportFriendlyMedia` (Magick q95 JPEG, ffmpeg libx264 CRF 18 + AAC); cache under `{library}/.exports/`; skip encode when already JPEG or H.264+AAC MP4; progress via WebSocket `gallery_export` events.
- **Rationale:** Keeps convert pipeline unchanged; quality-first exports; same skip rules as `.thumbnails` for scans.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Gallery export separate from library convert".
