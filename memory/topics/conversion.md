# Library and media conversion
Updated: 2026-11-17. Library folders, what gets encoded or moved, encoders, and file-safety rules.

## Now
The library has `originals/`, `processed/`, `error/` and `invalid/` ([processed-folder-and-promote](../notes/processed-folder-and-promote.md)); images become progressive AVIF via avifenc ([progressive-avif-avifenc-direct](../notes/progressive-avif-avifenc-direct.md)); library video stays GPU-only ([gallery-batch-trash-and-cpu-export](../notes/gallery-batch-trash-and-cpu-export.md)); encodes go through a staging dir ([convert-staging-ignore-xmp-log](../notes/convert-staging-ignore-xmp-log.md)); destructive steps need positive proof ([destructive-ops-need-positive-verification](../notes/destructive-ops-need-positive-verification.md)). Policy detail: `docs/playbooks/SpaceMaker-adaptations.md`.

## How it got here
- 2026-09-22 converted/ folder and GPU-only video ([note](../notes/library-folder-layout.md)); renamed processed/ on 2026-09-27 ([note](../notes/processed-folder-and-promote.md)).
- 2026-10-02 same-size duplicate rule corrected to byte-identical content ([note](../notes/as-is-move-duplicates-byte-identical.md)).

## Notes
- [Correction: as-is move duplicates require byte-identical content](../notes/as-is-move-duplicates-byte-identical.md) 2026-10-02: correction: drop a source as duplicate only when content is identical, else write name (2).ext
- [Destructive file operations need positive verification](../notes/destructive-ops-need-positive-verification.md) 2026-10-02: drop or delete a file only after positive proof (identical content, or local size == remote size); rmdir-only mount cleanup
- [ffmpeg out_time_ms is in microseconds](../notes/ffmpeg-out-time-ms-microseconds.md) 2026-10-02: ffmpeg's out_time_ms progress value is in microseconds, which made export progress jump to 99%
- [Convert-media: staging directory for atomic `processed/` writes; `--ignore-xmp`; rotating file log](../notes/convert-staging-ignore-xmp-log.md) 2026-09-28: encode into a same-volume staging dir for atomic processed/ writes; avifenc --ignore-xmp; rotating log
- [Easy Wi‑Fi convert: per-file start + live progress totals](../notes/easy-wifi-convert-per-file.md) 2026-09-28: Wi-Fi uploads start convert per file; progress total grows as files arrive
- [Progressive AVIF: avifenc-direct; Magick not removed](../notes/progressive-avif-avifenc-direct.md) 2026-09-28: avifenc --progressive directly on JPEG/PNG; Magick kept for thumbs, rasterizing and fallback
- [Promote uncompressed media; `converted/` → `processed/`; Settings chrome](../notes/processed-folder-and-promote.md) 2026-09-27: converted/ renamed processed/ (migrated on ensure); Compress off promotes originals as-is
- [Photo backup Compress media: disk preferences + Easy UI (full SDD)](../notes/compress-media-preference.md) 2026-09-26: Compress media preference on disk (preferences.json) with its own ports; full SDD
- [Photo Backup multi-file convert: batch-once trigger + in-place drain loop instead of per-file trigger + recursive requeue](../notes/photo-backup-convert-drain-loop.md) 2026-09-25: batch-once trigger + in-place drain loop instead of per-file recursive requeue
- [Start convert stops active extract](../notes/start-convert-stops-extract.md) 2026-09-22: starting convert stops an active extract gracefully first
- [Compression reference](../notes/compression-reference-script.md) 2026-09-22: docs/reference/convert_all_1_1.sh is the authoritative compression reference

## History (superseded)
- [Pre-1.0 bug-fix pass: collision naming and mount safety](../notes/pre-1-0-collision-and-mount-safety.md) 2026-10-02 → superseded by as-is-move-duplicates-byte-identical
- [GPU-only library video convert and gallery preview gating](../notes/gpu-only-video-and-preview-gating.md) 2026-09-22 → superseded by gallery-batch-trash-and-cpu-export
- [Library folder layout and conversion outcomes](../notes/library-folder-layout.md) 2026-09-22 → superseded by processed-folder-and-promote
