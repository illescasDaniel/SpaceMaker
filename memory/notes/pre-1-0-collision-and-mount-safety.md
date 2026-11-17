---
name: pre-1-0-collision-and-mount-safety
description: {stem}_{ext} outputs on same-stem collisions; rmdir-only mount cleanup; Move deletes only after size check
type: decision
date: 2026-10-02
status: superseded
supersedes:
superseded_by: as-is-move-duplicates-byte-identical
source:
---

Pre-1.0 bug-fix pass: collision naming and mount safety.

- **Context:** review before 1.0 found same-stem sources (png/jpg/heic, mov/mp4) sharing one planned output, so "skip existing output" deleted an original that was never encoded; RAW could overwrite a JPEG's AVIF. Separately, `shutil.rmtree` on a failed-unmount FUSE mount would delete real phone files.
- **Decision:** whenever the plain output name exists, any source extension uses `{stem}_{ext}.<out>` (RAW included); as-is moves never overwrite (same size = duplicate, else `name (2).ext`). Mount dirs are removed with `rmdir` only. Move mode deletes the device file only after local size == remote size.
- **Rationale:** idempotency must only match the file's own planned output; destructive operations need a positive verification first.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-02 — Pre-1.0 bug-fix pass: collision naming and mount safety".

Superseded by [as-is-move-duplicates-byte-identical](as-is-move-duplicates-byte-identical.md): its 'same size = duplicate' rule was corrected the same day; the mount and Move rules live on in destructive-ops-need-positive-verification.
