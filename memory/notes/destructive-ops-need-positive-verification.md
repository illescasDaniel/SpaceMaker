---
name: destructive-ops-need-positive-verification
description: drop or delete a file only after positive proof (identical content, or local size == remote size); rmdir-only mount cleanup
type: decision
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

Destructive file operations need positive verification first: a source is dropped as a duplicate only when its content is identical (size + 1 MiB chunk comparison), a device file is deleted after Move only when the local size equals the remote size, and mount directories are removed with `rmdir` only, never `shutil.rmtree`.

**Why:** a weaker check (same size alone) could destroy a file that was never safely copied, and `rmtree` on a FUSE mount whose unmount failed would delete real phone files (pre-1.0 review, 2026-10-02).
**How to apply:** any new delete/move path must verify first; prefer leaving a duplicate over losing a file.

Source: jevmem notes #42, #43 and consolidated #90 (pinned there), and `decisions.md` entries of 2026-10-02.
