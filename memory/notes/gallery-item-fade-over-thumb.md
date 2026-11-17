---
name: gallery-item-fade-over-thumb
description: full preview fades in over the thumb; Loading chip; side nav arrows
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Gallery item: fade-over-thumb + side nav + Loading chip.

- **Context:** Progressive item preview used a center spinner and dual fade (thumb out + full in), which flashed the empty stage; prev/next sat overlaid on the media and disabled arrows used low opacity so they vanished on boundary items.
- **Decision:** Fade full preview in over a still-visible thumb (hide thumb only after opaque); corner `• Loading…` chip (no spinner); prev/next in a 3-column layout beside the stage with media inset; disabled arrows stay fully opaque (muted only). Client CSS/JS only (`theme.css` `--dur-crossfade`, `shell-gallery.css` / `index.html`, `app.js`).
- **Rationale:** Matches approved wireframe/SPEC; eliminates blank flashes and keeps controls always readable without covering content.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Gallery item: fade-over-thumb + side nav + Loading chip".
