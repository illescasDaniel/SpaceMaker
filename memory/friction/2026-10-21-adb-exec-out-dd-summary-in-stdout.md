---
date: 2026-10-21
area: code
severity: wrong-result
status: fixed (adb_repository.read_range: dd status=none, uncommitted)
---

**Call:** `AdbDeviceRepository.read_range` = `adb exec-out "dd if=… iflag=skip_bytes,count_bytes skip=N count=L"` (Pixel 10a, toybox dd).
**Expected:** exactly L bytes.
**Got:** L + ~80 bytes: `exec-out` merges the remote stderr into stdout, so dd's "records in / records out / bytes copied" summary follows the range. Unit tests used a fake with a separate stderr and never saw it; Magick ignores bytes after the JPEG end marker, so an ad-hoc script "worked" while the use case's exact-length check (DNG previews) answered 404. Video posters (stream route) had been getting the extra bytes too.
**Workaround:** `status=none` on dd (errors still exit non-zero; their text arrives on stdout, which `_raise_adb_failure` already reads).
**Idea:** any new `exec-out` command must not write to stderr on success; test fakes for exec-out should put stderr text on stdout.
