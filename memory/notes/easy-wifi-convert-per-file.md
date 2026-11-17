---
name: easy-wifi-convert-per-file
description: Wi-Fi uploads start convert per file; progress total grows as files arrive
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Easy Wi‑Fi convert: per-file start + live progress totals.

- **Context:** The 2026-09-25 batch-once trigger waited until the whole multipart `/api/upload` finished before starting Easy convert, so folder uploads delayed conversion. Waiting was chosen so the initial `0/N` total was correct; starting on the first file previously baked in `total=1`. Spec already required convert to start when the first file lands.
- **Decision:** Trigger `maybe_start_convert_drain` after each saved/skipped Wi‑Fi file (from `handle_wifi_upload`); remove the batch-only `/api/upload` `finally`. While convert is `RUNNING`, refresh progress with `live_job_progress(completed, count(originals/))` so `total` grows as more files arrive mid-pass. Keep the in-place `_run_convert` drain loop; `on_progress` uses the same live formula so fixed pass scans cannot clobber a grown total.
- **Rationale:** Satisfies “convert as soon as photos start arriving” without regressing the multi-file progress display; live total is correct because the file currently encoding still sits in `originals/`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Easy Wi‑Fi convert: per-file start + live progress totals".
