---
name: usb-transfer-folder-enum
description: TransferFolder enum separate from media SourceFolder; list_file_paths for any file type
type: decision
date: 2026-09-26
status: current
supersedes:
superseded_by:
source:
---

USB file transfer: separate `TransferFolder` + `list_file_paths`; reuse Documents root and extract job control.

- **Context:** New Home module for cable-only arbitrary-file transfer (MTP/ADB/AFC) into Documents, no convert. Spec approved 2026-09-26. Needed domain/ports without conflating photo-library extract.
- **Decision:** (1) `TransferFolder` enum (Download/Documents/DCIM/Pictures/Movies/Music) separate from media-only `SourceFolder`, so extract defaults stay DCIM/Pictures/Movies. (2) Extend `DeviceRepositoryPort` with `list_file_paths` (any file type); keep `list_media_paths` for extract. Adapter bodies stubbed `NotImplementedError` until Phase 4. (3) Use case `TransferUsbFiles` writes under `documents_directory()/SpaceMaker/` via `documents_transfer_destination` (same root as Receive files), reuses `ExtractJobControl` + `extract_control_flags` for pause/stop. (4) `AppModule.USB_FILE_TRANSFER`; iPhone limit banner gated by `shows_iphone_limit_banner` (AFC only).
- **Rationale:** Extending `SourceFolder` would change extract’s `ALL_SOURCE_FOLDERS` defaults. A second list API avoids teaching media extractors to return PDFs. Shared Documents root matches Receive files UX; shared job control avoids a parallel pause/stop implementation.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-26 — USB file transfer: separate `TransferFolder` + `list_file_paths`; reuse Documents root and extract job control".
