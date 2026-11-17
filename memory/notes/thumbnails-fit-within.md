---
name: thumbnails-fit-within
description: user required thumbnails to keep the source aspect ratio; square crop is display-only
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Thumbnail generation: fit-within instead of crop-fill, so the cached JPEG preserves source aspect ratio.

- **Context:** `SubprocessThumbnailGenerator._thumb_image` used Magick `-thumbnail 320x320^ -gravity center -extent 320x320`, which scales to *cover* a 320×320 box and then crops the overflow — every cached thumbnail file is a hard square regardless of the source's real aspect ratio. `_thumb_video` extracted a full-resolution ffmpeg frame with no scaling at all. This mismatched the item-detail page, which already shows the thumbnail as a progressive placeholder via `object-fit: contain` (same aspect-fit as the full preview) — a pre-cropped square thumb doesn't line up with the full image's real framing, so the placeholder visibly "pops" into a different shape when the full image loads.
- **Decision:** User explicitly required (in chat) that thumbnail files preserve the source's exact aspect ratio, with cropping to a square remaining a **display-only** concern (grid `object-fit: cover`, unchanged). Changed `_thumb_image` to `-thumbnail 320x320>` (fit within a 320×320 box, longest side capped, proportional on the other axis; `>` skips upscaling smaller sources) with no `-gravity`/`-extent`. Changed `_thumb_video` to add `-vf "scale='min(320,iw)':'min(320,ih)':force_original_aspect_ratio=decrease"` so video thumbnails are also capped and aspect-correct instead of full-resolution. `specs/gallery/SPEC.md` gained an explicit "Thumbnail framing" bullet documenting this. New unit tests assert the exact Magick geometry string and the absence of `-extent`/`-gravity`, and assert the ffmpeg `-vf` scale filter.
- **Rationale:** Baking the square crop into the cached bytes was strictly worse than doing it in CSS: it threw away information the item-detail placeholder needed, for a benefit (matching the grid's square tiles) that `object-fit: cover` already gives for free at zero cost to the underlying asset. Verified against the real library (`C:\Users\kaumi\Pictures\SpaceMakerLibrary`, worktree-scoped dev server): source `IMG_5205.avif` is 3024×4032 (3:4); the old cached thumb was a cropped 320×320 square; after deleting it and re-requesting `/thumbs/IMG_5205.avif`, the regenerated file is 240×320 — exactly 3:4. Bulk-regenerating the rest of the real library's stale thumbnails was blocked by the auto-mode classifier (wildcard delete flagged as "Irreversible Local Destruction") even though `.thumbnails/` is documented as safe to delete anytime — left for the user to do (delete `.thumbnails/` or approve a permission rule), since old square thumbnails will simply be replaced by aspect-correct ones the next time each is requested (mtime-based staleness check won't force it on its own).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Thumbnail generation: fit-within instead of crop-fill, so the cached JPEG preserves source aspect ratio".
