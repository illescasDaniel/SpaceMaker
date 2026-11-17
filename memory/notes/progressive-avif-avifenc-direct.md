---
name: progressive-avif-avifenc-direct
description: avifenc --progressive directly on JPEG/PNG; Magick kept for thumbs, rasterizing and fallback
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Progressive AVIF: avifenc-direct; Magick not removed.

- **Context:** Gallery open speed plan adds progressive (layered) AVIF via `avifenc`. An earlier draft used Magick `-auto-orient` → temp PNG → `avifenc` for every image. User asked whether Magick could be dropped from that chain to save a dependency.
- **Decision:** Prefer `avifenc --progressive` **directly** on JPEG/PNG; RAW via ExifTool preview → `avifenc`; only Magick-rasterize formats `avifenc` cannot read (HEIC/TIFF/JXL/WebP/…). Keep Magick as a project dependency (thumbs, friendly JPEG, identify, rasterize, non-progressive fallback). Add `BundledTool.AVIFENC` + manifest entry; extend `GalleryIndexRow` with optional display-metadata fields for non-blocking item open.
- **Rationale:** Removes an unnecessary temp raster for the common case without pretending Magick can leave the tool graph. Managed download of official libavif release zips remains the packaging path (PATH/`pacman -S libavif` as fallback).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Progressive AVIF: avifenc-direct; Magick not removed".
