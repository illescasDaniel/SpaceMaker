---
name: phone-picker-replaces-adbfs
description: one in-app picker over adb shell / ifuse for USB transfer and photo backup; adbfs and native dialog removed
type: decision
date: 2026-10-19
status: current
supersedes: remove-mtp-adb-afc
superseded_by:
source:
---

In-app phone picker over `adb shell` replaces adbfs + native dialog.

- **Context:** USB file transfer Add files/folder needed `adbfs` (FUSE, only on Arch AUR, nothing for Ubuntu/macOS/Windows) plus a native dialog that does not exist in `--server-only`; photo backup had no way to pick a custom folder.
- **Decision:** one web picker screen lists the phone one directory per call (`DeviceRepositoryPort.list_directory`; `adb shell` for ADB, ifuse mount for iPhone) and serves both USB file transfer and USB photo backup Step 1. adbfs code, hints, packaging/legal rows and the native-dialog Browse route are removed in the same change set; ifuse stays.
- **Rationale:** no FUSE or extra download, identical on all OSs and in server-only mode; picks keep today's storage-relative path semantics so pipelines are unchanged. Spec: `specs/device-file-picker/SPEC.md` (the feature subsequently shipped).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-19 — In-app phone picker over `adb shell` replaces adbfs + native dialog".

Also replaces: [lazy-adbfs-mount](lazy-adbfs-mount.md).
