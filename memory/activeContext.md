_Last updated: 2026-09-28_

## Branch

`main`

## Current focus

**Aspect-preserving gallery thumbnails** — cache JPEGs keep original aspect (fit within max edge); grid still crops via `object-fit: cover`; item detail gets a better progressive placeholder. Save-changes landed prior gallery/convert work; starting Phase 0 wireframe + Phase 1 SPEC.

## Next steps

1. Phase 0 wireframe note (grid cover vs item contain on same aspect thumb) → UX approval.
2. Phase 1 gallery SPEC clarification → spec approval.
3. Then architecture/tests/impl (Magick `-thumbnail WxH` without `^`/`-extent`; video thumbs size-capped similarly; stale `.thumbnails/` need refresh).
4. Still open from prior: Progressive AVIF / gallery transition / Reset gallery / Easy convert / Early Photo Backup smoke; ADB; pywebview.

## Just changed (prior batch, now committing)

- Progressive AVIF encode + gallery open speed
- Gallery item progressive transition (fade-over-thumb, side nav, Loading chip)
- Easy Wi‑Fi convert per-file start + live totals
- Reset gallery closes SQLite before unlink (WinError 32)
