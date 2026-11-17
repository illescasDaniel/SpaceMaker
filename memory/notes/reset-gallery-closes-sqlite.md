---
name: reset-gallery-closes-sqlite
description: Reset closes the SQLite connection before deleting the index and its WAL/SHM files
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Reset gallery closes SQLite before deleting index.

- **Context:** `POST /api/library/reset` raised `PermissionError: [WinError 32]` on `.index.sqlite` because `SqliteGalleryIndex` caches an open connection (WAL), and Windows cannot unlink an open database.
- **Decision:** Add `GalleryIndexPort.close(library_root)`; `SqliteGalleryIndex.close` drops and closes the cached connection; `ResetLibrary` takes the index port and calls `close` before deleting `.index.sqlite` (+ WAL/SHM sidecars).
- **Rationale:** Keeps the unlock next to the wipe in the use case (not only in the HTTP handler); works on Windows without changing journal mode.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Reset gallery closes SQLite before deleting index".
