---
name: shell-r-aliases-kept
description: old R.* names kept as aliases instead of a mass rename in a bugfix
type: decision
date: 2026-09-29
status: superseded
supersedes:
superseded_by: web-ts-typing-pass-drop-r-registry
source:
---

Keep pre-rename `R.*` aliases on the shell runtime registry.

- **Context:** After the cleaner_code TypeScript split, core helpers were renamed (`api`→`apiSend`, `bindInfoPanelToggle`→`bindDisclosure`, `setQrImageSrc`→`setQrImage`) and only the new names were assigned onto `R`. Feature modules (`@ts-nocheck`) still called the old names, so bootstrap threw (`R.bindInfoPanelToggle is not a function`) and every gallery/settings fetch failed (`R.api is not a function`) — gallery stuck on "Loading more".
- **Decision:** Wire the old names as aliases on `R` in `api.ts`/`dom.ts` (and document them on `RuntimeRegistry`) rather than mass-renaming every feature call site in this bugfix.
- **Rationale:** Call sites are the majority surface; aliases restore the intended bag-of-helpers contract with minimal churn. Call sites can migrate to the new names later behind removing `@ts-nocheck`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Keep pre-rename `R.*` aliases on the shell runtime registry".

Superseded by [web-ts-typing-pass-drop-r-registry](web-ts-typing-pass-drop-r-registry.md).
