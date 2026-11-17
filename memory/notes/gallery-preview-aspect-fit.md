---
name: gallery-preview-aspect-fit
description: placeholder and full preview both aspect-fit; no CSS blur
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Gallery progressive preview: aspect-fit, no CSS blur, smooth scale.

- **Context:** Item-page placeholder used `object-fit: cover` plus `filter: blur(16px)` (and scale), while the full preview used `contain`. That made loading look cropped/blurred, then “snap” to fit; spinner was hard to see on busy images. User also asked for bilinear-like scaling so upscaled thumbs are not pixelated.
- **Decision:** Placeholder and full preview both use `object-fit: contain` and `image-rendering: auto`/`smooth`; drop CSS blur/scale on the thumb; give `.gallery-item-spinner` a disc backdrop. No domain/port changes (presentation only). Wireframe + gallery SPEC updated.
- **Rationale:** Loading state should match final framing; native low-res softness is enough; explicit smooth rendering avoids nearest-neighbor upscales.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Gallery progressive preview: aspect-fit, no CSS blur, smooth scale".
