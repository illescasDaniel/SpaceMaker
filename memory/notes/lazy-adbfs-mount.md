---
name: lazy-adbfs-mount
description: adbfs mounted lazily, never FUSE-walked on every snapshot
type: decision
date: 2026-09-27
status: superseded
supersedes:
superseded_by: phone-picker-replaces-adbfs
source:
---

Lazy adbfs mount; never FUSE-walk on every snapshot.

- **Context:** After Browse/adbfs landed, selecting ADB (wizard or USB transfer) froze the app. `enriched_snapshot` called `browse_root` whenever `device_id` was set — including USB photo-backup auto-select — then `os.walk` over the FUSE tree hung on entries like `.$Trash$`. Crash left `/tmp/spacemaker-adbfs-*` mounted.
- **Decision:** (1) Browse snapshot is a no-op outside `USB_FILE_TRANSFER`. (2) ADB presets use shell exist-probe; `mount_available` = adbfs on PATH; mount only via `POST /api/usb-transfer/mount` (Browse / extras). (3) Shallow top-level dir probe only; adbfs/ifuse/fusermount timeouts; orphan `/tmp/spacemaker-adbfs-*` cleanup on enter/mount.
- **Rationale:** Device listing and settings must stay fast; FUSE is only needed for the native Browse dialog.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — Lazy adbfs mount; never FUSE-walk on every snapshot".

Superseded by [phone-picker-replaces-adbfs](phone-picker-replaces-adbfs.md).
