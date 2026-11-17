---
name: usb-no-preset-precheck
description: no preset folders pre-checked; extras expanded by path-component matching
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

No preset pre-check; Browse extras expand via adb find.

- **Context:** User asked never to preselect folders. Browse-picked folders transferred 0 files because the queue only filtered `list_file_paths` (preset roots like Download/DCIM), so mount-relative extras like `WhatsApp/Media` never matched absolute `/sdcard/...` paths and were never discovered.
- **Decision:** (1) `default_transfer_folders` → empty; UI/session start with no checks. (2) Port `list_extra_file_paths`; ADB resolves extras under mount device root / common prefixes with `find`; AFC walks under mount. (3) `path_matches_extra_sources` matches consecutive path components so absolute ADB paths still align with mount-relative extras.
- **Rationale:** Presets are opt-in; Browse must transfer any picked tree, not only known library folders.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — No preset pre-check; Browse extras expand via adb find".
