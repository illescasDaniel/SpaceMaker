---
name: send-files-folder-zips-share-token
description: folders shared as on-demand zips; one share token reused until Clear/Home/quit
type: decision
date: 2026-09-23
status: current
supersedes:
superseded_by:
source:
---

Send files: folder zips and stable LAN share token.

- **Context:** Phone download listed every file inside a shared folder; adding items regenerated the share token and forced a new QR scan; canceling the folder picker duplicated the last path.
- **Decision:** Manifest is one row per top-level selection (file or `folder_zip`); folders download as on-demand `.zip` with preserved relative paths. Share `?t=` token is created on first item and reused until Clear/Home/quit. Selection dedupes by resolved path; share folder picker returns empty string on cancel.
- **Rationale:** Matches user mental model (one folder → one download); one QR session for batch sharing from desktop.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — Send files: folder zips and stable LAN share token".
