---
name: gallery-delete-in-place
description: deleting removes the tile in place and never reloads the timeline; removal starts after the fade-in
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

Gallery delete: remove the tile in place, never reload the timeline.

- **Context:** First implementation of the spec'd removal animation called `loadGallery()` after the fade; it emptied `#timeline-view` (blank flash) and reset scroll. Before that, the removal fade also started together with the screen's own `screen-fade-in` (`--dur-base`) and was invisible.
- **Decision:** `removeGalleryItem(path)` waits `--dur-base`, fades the mounted tile, removes it (timeout fallback, since `transitionend` can be late or never fire), and mutates `S.galleryMonthBlocks` in place (`forgetGalleryItem`: mounted count, emptied month block, year-heading handoff). `showView` gained `skipGalleryReload`. Full `loadGallery()` remains only when nothing was ever loaded (deep link).
- **Rationale:** The windowed timeline keeps its own item state, so in-place mutation is cheap and correct; a reload trades a visible glitch for re-syncing data we already know. Trade-off: a stale server-side change (e.g. another import) shows up only on the next normal gallery entry.

Added from jevmem (2026-10-01): the removal starts after the screen fade-in so that it is visible.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Gallery delete: remove the tile in place, never reload the timeline".
