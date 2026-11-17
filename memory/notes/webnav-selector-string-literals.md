---
name: webnav-selector-string-literals
description: webnav selector counts exact-name JS string literals as references
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

webnav `selector`: treat exact-name JS string literals as references.

- **Context:** Tool review found `selector("#btn-gallery-item-back")` reported no JS usage although `gallery.ts` binds it via the project helper `onClick("btn-gallery-item-back", …)`; the same helper pattern covers 44 call sites (plus `bindDisclosure`, `setQrUrlField`, …). A Cursor agent had used `selector` to confirm "nothing left behind" after removing a class — false completeness is the worst failure mode for that tool.
- **Decision:** Record every JS/TS string literal that is a bare identifier-like name (not concatenated); `format_selector` reports those equal to the query's bare name as `string literal` hits, except on lines a recognized DOM API already covers (so `getElementById("x")` doesn't also show as a `.x` class hit). They also count as references for the unreferenced-selector diagnostic.
- **Rationale:** Generic (no per-project helper list to configure, keeps the servers reusable); exact-name literals are a strong signal and clearly labeled as lower-confidence. Rejected: a `WEBNAV_MCP_ID_HELPERS` env var — every new helper would silently regress until someone updated config.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — webnav `selector`: treat exact-name JS string literals as references".
