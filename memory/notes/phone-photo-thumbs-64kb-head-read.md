---
name: phone-photo-thumbs-64kb-head-read
description: EXIF thumbnail from the first 64 KB (97% of camera JPEGs); full pull <=25 MB as fallback; 4 parallel reads
type: decision
date: 2026-10-20
status: current
supersedes:
superseded_by:
source:
---

Phone photo thumbnails: 64 KB head read for the EXIF thumbnail, full pull as the fallback.

- **Context:** the phone picker's photo previews need a thumbnail strategy over ADB. A0 spike on a Pixel (Android 17), see `specs/device-file-picker/PLAN-media-preview.md`.
- **Decision:**
  - Read the first 64 KB with `adb exec-out head -c 65536`, then extract the EXIF `ThumbnailImage` and orient it.
  - If there is no embedded thumbnail, pull the full file to a temp location and run Magick `-thumbnail 320x320>`, under a size cap of about 25 MB. Above the cap, show the icon.
  - Run 4 parallel reads.
  - Cache on disk with LRU.
  - The lightbox uses a full pull and a 1600 px rendition.
  - Videos come later, through a loopback HTTP Range route backed by `dd iflag=skip_bytes,count_bytes`.
- **Rationale:** 97% of camera JPEGs carry a 504×378 thumbnail in the first 55 KB, which costs 40–100 ms against 210–340 ms for a full pull. Parallel exec-out scales to 20 ms per read with 4 workers. In range tests, ffmpeg needed about 1.5 s and under 13 MB for one frame of a 416 MB MP4, even though `moov` is at the tail.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-20 — Phone photo thumbnails: 64 KB head read for the EXIF thumbnail, full pull as the fallback".
