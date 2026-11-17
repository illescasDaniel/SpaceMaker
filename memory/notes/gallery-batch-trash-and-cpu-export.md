---
name: gallery-batch-trash-and-cpu-export
description: send2trash only (no hard delete); gallery MP4 export may use CPU libx264 after a 409 confirm; library convert stays GPU-only
type: decision
date: 2026-10-18
status: current
supersedes: gpu-only-video-and-preview-gating
superseded_by:
source:
---

Gallery batch: send2trash, CPU libx264 behind a confirm, zips in `.exports/.batch`.

- **Context:** users need to delete/convert many gallery items at once; deletion must be recoverable and conversion must work without a GPU encoder.
- **Decision:** `send2trash` (new dependency) behind `TrashPort` with no hard-delete fallback; library convert stays hardware-only, but gallery MP4 export may use `libx264` after a 409 `cpu_confirm_required` confirm (client retries with `allow_cpu_encode`); batch zips live in `.exports/.batch/{job_id}/` with a 24 h sweep and are deleted after download; max 500 items per request.
- **Rationale:** trash keeps mistakes reversible; the confirm keeps the slow CPU path an explicit choice; the existing `.exports/` cache dir needs no new storage root.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-18 — Gallery batch: send2trash, CPU libx264 behind a confirm, zips in `.exports/.batch`".

The earlier [library encoder decision](gpu-only-video-and-preview-gating.md) remains in force: prefer hardware AV1 (nvenc, qsv, vaapi), then hardware H.264, then move video unchanged; browser preview excludes HEVC. This avoids silent CPU transcodes and respects web playback limits. The CPU fallback in this note applies to gallery export.
