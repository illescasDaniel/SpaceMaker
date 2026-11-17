---
name: photo-backup-convert-drain-loop
description: batch-once trigger + in-place drain loop instead of per-file recursive requeue
type: decision
date: 2026-09-25
status: current
supersedes:
superseded_by:
source:
---

Photo Backup multi-file convert: batch-once trigger + in-place drain loop instead of per-file trigger + recursive requeue.

- **Context:** User reported that uploading multiple photos in one Photo Backup batch (e.g. a folder from an Android phone) saved every file but converted only one, with the rest sitting unconverted until the user left and re-entered Photo Backup; the convert progress display also reset to "0/1" per file instead of showing one running total across the batch (expected "0/2" → "1/2" → "2/2" for two photos).
- **Root causes, both in `src/spacemaker/bootstrap/services.py`:** (1) `_run_convert`'s logic for "more files arrived while this job was converting" called `self.start_convert(...)` recursively from inside the very function running as `self._convert_future`'s target; `_convert_job_active()` checks `not self._convert_future.done()`, which is still `False` (not done) at that point, so the requeue call silently no-opped — the leftover file only got picked up when something unrelated (re-entering Photo Backup) started a brand-new job from scratch. (2) The old per-file trigger (`handle_wifi_upload`, called once per file from `/api/upload`'s per-file loop in `src/spacemaker/adapters/inbound/web/app.py`) started the convert job as soon as the *first* file in a batch landed on disk, baking in `total=1` from the very start of the job — the true batch size was only known once the whole HTTP request's file loop finished.
- **Decision:** Turned the recursive requeue into an in-place `while True` drain loop inside `_run_convert` itself (same thread/future, so no reentrancy trap), tracking a `cumulative_completed` count across loop passes and offsetting each pass's `on_progress` callback by it so the UI shows one running total instead of resetting per pass. Separately, renamed `_maybe_start_convert_drain` to public `maybe_start_convert_drain` and moved its call site from inside `handle_wifi_upload` (fired once per file) to `/api/upload`'s route handler (fired once per request, in a `finally` around the file loop so it still fires if a later file in the batch fails) — so by the time the convert job starts, every file from that batch is already on disk and its initial total is correct from the first progress event.
- **Rationale:** The drain loop fixes correctness (no file is ever silently stuck until the user re-enters Photo Backup) independent of the trigger-timing fix; the batch-once trigger fixes the common case (small/fast batches) so the progress bar's total is right from the start rather than needing a second drain pass to correct itself. Both were kept because either one alone leaves a gap: drain-loop-only still shows a transient wrong total before self-correcting; batch-trigger-only doesn't help if more files arrive from a *later* upload request while an earlier batch's conversion is still running. Verified: `uv run ruff check` clean, full `uv run pytest` green (179 passed, 5 pre-existing unrelated skips); not yet confirmed on real Windows/Android hardware — awaiting user retest.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-25 — Photo Backup multi-file convert: batch-once trigger + in-place drain loop instead of per-file trigger + recursive requeue".
