---
name: transfer-files-ephemeral-staging
description: Transfer files stage bytes in an ephemeral root; SHA-256 dedupes same-name items
type: decision
date: 2026-09-25
status: current
supersedes:
superseded_by:
source:
---

Transfer files: ephemeral staging + SHA-256 name collision; fifth Home module.

- **Context:** New bidirectional LAN session (PC + phones upload/download). User chose keep Receive/Send and add a fifth Home tile; same display name with different content gets auto-suffix (`report (2).pdf`). Spec approved 2026-09-25.
- **Decision:** Session bytes live only under an ephemeral staging root (not Documents, not library). `ContentHasher` outbound port (`sha256_file`) feeds `StageTransferItem`; domain `allocate_transfer_display_name` skips when name+hash match and otherwise suffixes before the final extension. Folders become one `FOLDER_ZIP` row via existing `write_folder_zip`. `AppModule.TRANSFER_FILES` / `LanSessionKind.TRANSFER_FILES` added. HTTP/UI wiring deferred to Phase 4 after architecture approval.
- **Rationale:** Hash-on-collision matches the approved spec without path-only skip (receive/send). A dedicated hasher port keeps hashing out of domain and out of FastAPI handlers. Reusing share’s zip helper avoids a second zip implementation.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-25 — Transfer files: ephemeral staging + SHA-256 name collision; fifth Home module".
