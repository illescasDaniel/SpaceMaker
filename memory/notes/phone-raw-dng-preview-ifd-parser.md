---
name: phone-raw-dng-preview-ifd-parser
description: stdlib IFD parser over range reads finds the DNG's embedded JPEG; ~0.2 s instead of 8-27 MB pulls
type: decision
date: 2026-10-21
status: current
supersedes:
superseded_by:
source:
---

Phone RAW (DNG) previews: embedded JPEG located by a pure-Python IFD parser over range reads.

- **Context:** Phase C of `specs/device-file-picker/PLAN-media-preview.md`. C0 spike on a Pixel 10a: Pixel and iPhone ProRAW DNGs hold exactly one displayable JPEG, in IFD0 (Pixel 1280×960 with no EXIF, stored unrotated; iPhone full size with its own EXIF Orientation). 5 of 9 Pixel originals keep IFD0 ~6 KB before EOF, with its out-of-line values ~1.77 MB away. Snapseed `.dng` files are plain JPEGs; Lightroom proxies are JPEG XL tiles.
- **Decision:**
  - Sniff the first 4 KB: `FF D8` → the photo strategy unchanged; a TIFF header → `domain/dng_preview.py` (stdlib only, I/O injected as `read_at`) walks IFD0, then up to 8 SubIFDs, with hard caps (64 entries, 8 MB preview, offsets within `stat_file` size, cycle detection); anything else → no preview.
  - BitsPerSample is checked only when its values are in the bytes already read, so tail-IFD0 files need no third read; the `FF D8` check and the Magick decode still guard.
  - New port method `PreviewImagingPort.render_embedded_jpeg(jpeg, max_edge, fallback_orientation, timeout_s)`: the preview's own EXIF Orientation wins, else `-orient <name>` from IFD0 before the stdin input + `-auto-orient`; never both, never enlarged.
  - No demosaicing, no rawpy/libraw/exiftool dependency, no 25 MB cap for TIFF DNGs (never fully pulled).
- **Rationale:** 1–2 small header reads plus one preview read (~0.2 s, 0.2–4 MB) instead of 8–27 MB full pulls; a bounded stdlib parser keeps untrusted bytes out of native libraries and adds no packaging weight.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-21 — Phone RAW (DNG) previews: embedded JPEG located by a pure-Python IFD parser over range reads".
