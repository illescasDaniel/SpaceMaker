---
name: library-folder-layout
description: library root originals/ converted/ error/ invalid/; one retry then error/
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: processed-folder-and-promote
source:
---

Library folder layout and conversion outcomes.

- **Context:** User refined conversion vs `convert_all_1_1.sh` with two-folder workflow extended to four outcomes.
- **Decision:** Library root contains `originals/`, `converted/`, `error/`, `invalid/`. Successful encode or move-as-is removes source from `originals/`. Failed encode: one retry, then `error/`. Unsupported/broken: `invalid/`. UI warnings with Review / Move-to-converted for errors.
- **Rationale:** Clear separation for gallery (`converted/` only), user review paths, and idempotent convert pipeline.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Library folder layout and conversion outcomes".

Superseded by [processed-folder-and-promote](processed-folder-and-promote.md): converted/ renamed processed/; the retry and error/ invalid/ outcomes still hold.
