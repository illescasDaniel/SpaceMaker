---
name: wifi-extract-default
description: Wi-Fi phone upload with a session token is the default extract method
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

Wi‑Fi extract as default (tokenized LAN upload).

- **Context:** USB MTP/ADB friction; users want cable-free transfer from any phone browser on the same LAN.
- **Decision:** `ConnectionMethod.WIFI` default on Step 1; **Start extract** mints a session token in the upload QR/URL; multipart POST to `/api/upload` writes to `originals/` via `ReceiveUploadedMedia` + `FileSystemPort.copy_file`. Move disabled for Wi‑Fi. USB paths unchanged. Dependency: `python-multipart`.
- **Rationale:** Reuses existing LAN bind and segno QR pattern; no open LAN ingest without an active session; hexagonal split (no `DeviceRepository` for Wi‑Fi).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Wi‑Fi extract as default (tokenized LAN upload)".
