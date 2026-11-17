---
name: as-is-move-duplicates-byte-identical
description: correction: drop a source as duplicate only when content is identical, else write name (2).ext
type: decision
date: 2026-10-02
status: current
supersedes: pre-1-0-collision-and-mount-safety
superseded_by:
source:
---

Correction: as-is move duplicates require byte-identical content.

- **Context:** the entry below says "same size = duplicate"; that was too weak and could drop a different file.
- **Decision:** `_move_to_folder` drops the source only if `files_have_same_content` (size + 1 MiB chunk compare); otherwise `name (2).ext`. Same for the post-encode duplicate collapse.
- **Rationale:** never lose data on a size coincidence.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-02 — Correction: as-is move duplicates require byte-identical content".

The same-stem collision decision from [the 2026-10-02 safety pass](pre-1-0-collision-and-mount-safety.md) still applies: distinguish same-name inputs of different extensions using `{stem}_{ext}` to avoid assigning them the same output. Its purpose is to avoid treating one source’s output as another’s.
