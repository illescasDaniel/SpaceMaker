---
name: gallery-qr-segno
description: QR codes via segno in the web adapter; lazy thumbnails under .thumbnails/
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

Gallery QR via segno (adapter-only).

- **Context:** Step 3 and LAN sharing need a scannable QR for `/gallery`; domain must stay free of QR libraries.
- **Decision:** Add `segno` as a runtime dependency; generate SVG at `GET /api/gallery/qr.svg` in the FastAPI adapter. Thumbnails lazy-generated under `{library}/.thumbnails/` via `SubprocessThumbnailGenerator` (ImageMagick / FFmpeg).
- **Rationale:** Keeps hexagonal boundaries; small dependency; EXIF dates via existing bundled ExifTool on `MediaProbePort.captured_at`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Gallery QR via segno (adapter-only)".
