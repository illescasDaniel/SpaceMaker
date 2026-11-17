---
name: usb-transfer-add-files-flatten-prefixes
description: Android storage prefixes (storage/emulated/0, sdcard...) stripped from destination paths
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

USB transfer: Add files/folder + flatten Android storage prefixes.

- **Context:** Browse was folder-dialog-first (files only after cancel). Destination paths kept Android roots (`storage/self/primary/…`, `sdcard/…`), creating deep unused folder trees under Documents/SpaceMaker.
- **Decision:** (1) UI: **Add files…** + **Add folder…** (native dialogs cannot mix). (2) Domain `strip_android_user_storage_prefix` applied in `documents_transfer_destination` and `normalize_device_relative_path` (extras). Prefixes: `storage/self/primary`, `storage/emulated/0`, `sdcard`. (3) Keep adbfs `subdir=` preference so the dialog opens on user storage when possible.
- **Rationale:** Matches Send/Transfer dual-picker UX; destinations read as `Download/…` / `WhatsApp/…` instead of mount aliases.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — USB transfer: Add files/folder + flatten Android storage prefixes".
