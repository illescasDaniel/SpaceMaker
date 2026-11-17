---
name: adb-exec-out-merges-stderr
description: adb exec-out merges remote stderr into stdout: dd needs status=none or ranges get ~80 extra bytes
type: gotcha
date: 2026-10-21
status: current
supersedes:
superseded_by:
source:
---

`adb exec-out` merges the remote stderr into stdout, so `dd` appended its "records in/out" summary to the requested byte range (L + ~80 bytes). Unit tests used a fake with separate stderr and never saw it; Magick ignored the trailing bytes, while the DNG preview's exact-length check returned 404. Video posters had been receiving the extra bytes too. Fixed with `status=none` in `AdbDeviceRepository.read_range` (confirmed at HEAD 2026-11-17).

**How to apply:** any new `exec-out` command must write nothing to stderr on success; test fakes for exec-out should put stderr text on stdout.

Source: `memory/friction/2026-10-21-adb-exec-out-dd-summary-in-stdout.md`.
