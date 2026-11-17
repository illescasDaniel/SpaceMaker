---
name: info-panels-and-url-field-components
description: one info-panel binding and one copyable URL field; execCommand fallback because LAN pages are plain http
type: decision
date: 2026-10-18
status: current
supersedes:
superseded_by:
source:
---

One ⓘ helper and one URL field component for the desktop UI.

- **Context:** six ⓘ buttons were dead because `bindDisclosure` toggled `hidden` while `.info-panel` is shown by `.visible`; long LAN URLs overflowed cards and could not be copied (plain-`http` LAN pages have no `navigator.clipboard`).
- **Decision:** every `.info-btn[aria-controls]` is bound by `bindInfoPanels` (`.visible` + aria sync + Escape); every phone/gallery URL is a `.url-field` (readonly input + `.url-copy`) driven by `setUrlField`, with secure-context clipboard then `execCommand` fallback and no "Copied" unless the copy succeeded. A Python markup test fails if an ⓘ has no panel.
- **Rationale:** one code path cannot drift per panel; the fallback is required because the phone gallery is served over plain http.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-18 — One ⓘ helper and one URL field component for the desktop UI".
