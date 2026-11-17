---
name: usb-browse-mount-extras-mtp-first
description: Browse extras scoped to the mount, presets shown only if they exist (MTP first)
type: decision
date: 2026-09-27
status: superseded
supersedes:
superseded_by: remove-mtp-adb-afc
source:
---

USB transfer Browse: mount-scoped extras + exist-only presets (MTP first).

- **Context:** Users need to see which common phone folders exist and add more sources via the OS file dialog at the phone mount. Spec approved; arch gate skipped once for MTP delivery.
- **Decision:** (1) `DeviceRepositoryPort.browse_root` — MTP returns GVFS path when mounted; ADB returns None until adbfs; AFC returns ifuse mount. (2) Probe preset folders from directory names under the mount; UI hides missing labels. Without a mount, show full catalog + Browse disabled. (3) Session `transfer_extra_paths` (device-relative); DesktopApi `choose_device_folder` then `choose_device_files` at mount; `POST /api/usb-transfer/extras` maps host picks under mount. (4) `TransferUsbFiles` queue = presets ∪ extras.
- **Rationale:** Native dialogs only work on real host mounts; GVFS is the existing MTP path. Extras stay mount-scoped to avoid escaping into the PC filesystem.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — USB transfer Browse: mount-scoped extras + exist-only presets (MTP first)".

Superseded by [remove-mtp-adb-afc](remove-mtp-adb-afc.md).
