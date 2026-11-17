# Phone access over USB
Updated: 2026-11-17. How SpaceMaker reaches Android and iPhone over USB, and the in-app phone picker.

## Now
An in-app picker lists the phone one directory at a time over `adb shell` (iPhone: ifuse) for USB transfer and photo backup ([phone-picker-replaces-adbfs](../notes/phone-picker-replaces-adbfs.md)), with keyset paging and a listing cache ([phone-picker-keyset-cursor-listing-cache](../notes/phone-picker-keyset-cursor-listing-cache.md)), server-side sort ([phone-picker-server-side-sort-v2-cursor](../notes/phone-picker-server-side-sort-v2-cursor.md)), grid view, and previews for photos, videos and DNG ([phone-photo-thumbs-64kb-head-read](../notes/phone-photo-thumbs-64kb-head-read.md), [phone-video-posters-range-route](../notes/phone-video-posters-range-route.md), [phone-raw-dng-preview-ifd-parser](../notes/phone-raw-dng-preview-ifd-parser.md)).

## How it got here
- 2026-09-22 MTP default with libmtp, ADB recommended ([note](../notes/mtp-default-adb-recommended.md)).
- 2026-09-27 MTP removed; ADB + adbfs and AFC + ifuse, adbfs mounted lazily ([note](../notes/remove-mtp-adb-afc.md)).
- 2026-10-19 adbfs and the native dialog replaced by the in-app picker over adb shell ([note](../notes/phone-picker-replaces-adbfs.md)).

## Notes
- [Phone RAW (DNG) previews: embedded JPEG located by a pure-Python IFD parser over range reads](../notes/phone-raw-dng-preview-ifd-parser.md) 2026-10-21: stdlib IFD parser over range reads finds the DNG's embedded JPEG; ~0.2 s instead of 8-27 MB pulls
- [Phone picker grid view: per-folder choice, server-side folder types and counts](../notes/phone-picker-grid-view-resolution.md) 2026-10-21: per-folder choice, then folder-type table, then auto-detect (>=1 media, >=60%); counts server-side
- [adb exec-out merges stderr into stdout](../notes/adb-exec-out-merges-stderr.md) 2026-10-21: adb exec-out merges remote stderr into stdout: dd needs status=none or ranges get ~80 extra bytes
- [Phone video posters: first frame over a loopback token-gated Range route, no playback](../notes/phone-video-posters-range-route.md) 2026-10-20: first frame via a loopback token Range route; ffmpeg whitelists; own 16-thread limiter avoids self-deadlock
- [Phone photo thumbnails: 64 KB head read for the EXIF thumbnail, full pull as the fallback](../notes/phone-photo-thumbs-64kb-head-read.md) 2026-10-20: EXIF thumbnail from the first 64 KB (97% of camera JPEGs); full pull <=25 MB as fallback; 4 parallel reads
- [Phone picker sorting is server-side with a sort-aware v2 cursor and a server-stored preference](../notes/phone-picker-server-side-sort-v2-cursor.md) 2026-10-19: sort carried in a v2 keyset cursor; preference stored server-side; cross-sort cursors rejected
- [Phone picker pages by keyset cursor over an application-level listing cache](../notes/phone-picker-keyset-cursor-listing-cache.md) 2026-10-19: 30 s TTL / LRU 8 listing cache, 100-entry keyset pages, filtering server-side
- [Empty ADB/iPhone device list auto-retries in the frontend only](../notes/device-list-auto-retry-frontend.md) 2026-10-19: empty ADB/iPhone list retries every 3 s, max 5, in the UI only; backend stays stateless
- [In-app phone picker over `adb shell` replaces adbfs + native dialog](../notes/phone-picker-replaces-adbfs.md) 2026-10-19: one in-app picker over adb shell / ifuse for USB transfer and photo backup; adbfs and native dialog removed
- [USB transfer: Add files/folder + flatten Android storage prefixes](../notes/usb-transfer-add-files-flatten-prefixes.md) 2026-09-27: Android storage prefixes (storage/emulated/0, sdcard...) stripped from destination paths
- [No preset pre-check; Browse extras expand via adb find](../notes/usb-no-preset-precheck.md) 2026-09-27: no preset folders pre-checked; extras expanded by path-component matching
- [USB file transfer: separate `TransferFolder` + `list_file_paths`; reuse Documents root and extract job control](../notes/usb-transfer-folder-enum.md) 2026-09-26: TransferFolder enum separate from media SourceFolder; list_file_paths for any file type

## History (superseded)
- [Lazy adbfs mount; never FUSE-walk on every snapshot](../notes/lazy-adbfs-mount.md) 2026-09-27 → superseded by phone-picker-replaces-adbfs
- [Remove MTP; ADB + adbfs / AFC + ifuse for USB](../notes/remove-mtp-adb-afc.md) 2026-09-27 → superseded by phone-picker-replaces-adbfs
- [USB transfer Browse: mount-scoped extras + exist-only presets (MTP first)](../notes/usb-browse-mount-extras-mtp-first.md) 2026-09-27 → superseded by remove-mtp-adb-afc
- [Unified libmtp for MTP adapter](../notes/libmtp-unified.md) 2026-09-22 → superseded by remove-mtp-adb-afc
- [MTP default, ADB recommended](../notes/mtp-default-adb-recommended.md) 2026-09-22 → superseded by remove-mtp-adb-afc
