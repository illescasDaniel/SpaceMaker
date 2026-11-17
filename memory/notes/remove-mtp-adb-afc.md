---
name: remove-mtp-adb-afc
description: MTP removed; USB is ADB (+adbfs) for Android and AFC + ifuse for iPhone
type: decision
date: 2026-09-27
status: superseded
supersedes: usb-browse-mount-extras-mtp-first
superseded_by: phone-picker-replaces-adbfs
source:
---

Remove MTP; ADB + adbfs / AFC + ifuse for USB.

- **Context:** MTP via libmtp/GVFS was unreliable (exclusive USB with Dolphin `mtp:/`, busy-device panics). User asked to strip MTP app-wide and ship ADB + iPhone Browse.
- **Decision:** (1) Delete `ConnectionMethod.MTP`, `MtpDeviceRepository`, libmtp tools from packaging/Components/docs. (2) USB file transfer defaults to **ADB**; extract keeps Wi‑Fi default with ADB/AFC cable options only. (3) Cache device repos on `AppServices`; `AdbDeviceRepository.browse_root` mounts via **adbfs** (`ANDROID_SERIAL`, PATH-only); shell exist-probe when adbfs missing so presets/transfer still work; AFC Browse via existing ifuse. (4) `release_device_mounts` on module enter/leave/Home/shutdown and connection-method change.
- **Rationale:** One Android cable path users already authorize (USB debugging); FUSE mounts give native Browse dialogs without fighting the OS MTP stack. adbfs is not catalog-downloaded (distro/AUR).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — Remove MTP; ADB + adbfs / AFC + ifuse for USB".

Also replaces: [mtp-default-adb-recommended](mtp-default-adb-recommended.md), [libmtp-unified](libmtp-unified.md).

Superseded by [phone-picker-replaces-adbfs](phone-picker-replaces-adbfs.md): adbfs replaced by the in-app picker over adb shell; ifuse for iPhone stays.
