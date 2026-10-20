# Plan — media previews in the phone picker

_Drafted 2026-10-20. Status: Phase A done (committed); Phase B (video posters) implemented, grader PASS, uncommitted; B2 and C not started._ Lifts the "Thumbnails/previews of phone files" out-of-scope line in `SPEC.md`. Each phase below is its own SDD revision (Phase Gates 0→5), on its own worktree branch.

Phase A done 2026-10-20 (SDD phases 0–5, grader PASS; commits 84a05f7, 2ef79bd). Phase B (videos) started 2026-10-20. After B0, the user chose **posters only** (first frame, duration badge, large frame in the lightbox, no playback), because the bundled Qt WebEngine cannot decode H.264/HEVC/AAC. Playback moves to Phase B2 (below). Phase C (RAW) planned below.

## What exists today (survey 2026-10-19)

- Picker rows (`web/src/device-picker.ts` `makeRow`) are a list with a 📁/📄 `dp-ico` span, the natural thumbnail slot. Pages of 100 rows, IntersectionObserver sentinel.
- `DeviceEntry` = `name, is_dir, size, mtime`. Media detection is only in the TS (`MEDIA_EXTENSIONS`, `isMediaName`).
- Byte access is whole-file only: `DeviceRepositoryPort.pull_file` (ADB `sync.pull`, no timeout; AFC `shutil.copy2` from the ifuse mount).
- Thumbnails exist only for the library: `SubprocessThumbnailGenerator.ensure_thumb(library_root, relative_path)` (Magick `-thumbnail 320x320>`, ffmpeg first frame, JPEG), cache under `<library>/.thumbnails/`, route `GET /thumbs/...` with ETag/304.
- The gallery viewer (`renderGalleryItemStage`) is tied to library paths. There is no standalone lightbox.
- Host Magick has libheif (HEIC rw), and exiftool and ffmpeg are present.
- `/api/device/*` is loopback-only. Phone previews must stay off `LAN_ALLOWED_ROUTES`.

## Phase A — photo previews (first)

**A0 Spike (real phone, read-only, about 30 min).** The questions to answer:

- Does `adb exec-out head -c 64K` give a usable EXIF thumbnail for the phone's JPEG/HEIC?
- How long does it take compared with a full pull?
- Does toybox `dd` support byte-offset reads?
- What is the cost of 4 parallel reads compared with sequential ones?

The outcome picks the strategy below. Record it in `decisions.md`.

**A0 result (2026-10-20, Pixel, Android 17, toybox 0.8.13).** The phone has no HEIC, so HEIC still needs checking on another phone. Host Magick has libheif.

- A full pull of a camera JPEG (3–6 MB) takes 0.21–0.34 s. A 64 KB head read takes 0.04–0.10 s.
- 97% of camera JPEGs have an EXIF thumbnail in the first 55 KB, at 504×378 and already upright. WhatsApp JPEGs have none (0 of 28). Screenshots: 2 of 3.
- DNG has no thumbnail in its head, but there is a 1280×960 `PreviewImage` at an offset that a `dd` range read can fetch.
- Parallel `exec-out` reads scale: 80 ms per read with 1 worker, 20 ms with 4, 14 ms with 8.
- Magick takes 0.05–0.15 s per 320 px thumbnail and up to 0.2 s per 1600 px lightbox rendition.
- `dd iflag=skip_bytes,count_bytes` works, which matters for Phase B. All sampled MP4s have `moov` at the tail. Through an adb-dd Range server, ffmpeg grabbed one frame in about 1.5 s using 8–13 MB, whatever the file size, which was under 3% of a 416 MB clip.

**Strategy (confirmed by A0):**

1. **Partial read first.** Read the first N KB (N about 64–256), then extract the EXIF/HEIC embedded thumbnail, then auto-orient it, then resize to 320 px. Typical cost is one round trip.
2. **Fallback.** Pull the full file into a temp location, run Magick `-auto-orient -thumbnail 320x320>`, then delete the temp file. Only do this under a size cap (for example 25 MB). Above the cap, show a generic tile.
3. **Cache.** Keep the cache outside the library, in an app cache dir under `device-thumbs/`. Key it on the hash of (device id, path, size, mtime). Size it by LRU (for example 200 MB). Writes are atomic.

**Architecture sketch (Phase 2 gate):**

- Domain:
  - `DevicePreviewKey` (device id, path, size, mtime).
  - A `PreviewKind` classifier, which moves the media-extension list server-side so the TS stops being the only source.
- Ports:
  - `DeviceRepositoryPort.read_head(device_id, path, max_bytes, timeout)`. ADB uses `exec-out head -c`. AFC reads from the mount.
  - A new `DeviceThumbnailPort` (extract embedded thumb, resize).
  - The cache as a port.
- Use case `GetDevicePreview`. It owns a concurrency limit of 2, yields to running transfer/extract jobs, and has a per-file timeout.
- Route `GET /api/device/thumb?device=…&path=…&size=…&mtime=…`. It is loopback-only, reuses the picker's path validation, and returns JPEG with an ETag. A failure returns 404/503, and the UI then keeps the icon.

**UI (Phase 0 wireframe, `#view-device-picker`):**

- A 40–48 px thumbnail replaces `dp-ico` on image rows. It lazy-loads only while visible, and the request is cancelled when scrolled away or when the folder changes.
- Clicking the thumbnail, or a 👁 button, opens a simple **lightbox**. It shows the 320 px thumbnail at once, then a larger 1600 px "preview" rendition produced by the same pipeline. It has ←/→ to step through image rows in the current page, and Esc to close. Selection checkboxes are unchanged.
- An optional list/grid toggle is deferred. Note it in out-of-scope unless the wireframe review wants it.

**Agent split:**

- The main session runs the gates, the wireframe review and the code review.
- Sonnet subagents do the spike (A0), the Phase 3 tests, the Phase 4 backend, and the Phase 4 TS/CSS.
- The `code-grader` subagent does Phase 5.

## Phase B — video previews (later)

Pulling a multi-hundred-MB file for one frame is not acceptable, and MP4 `moov` is often at the tail. The plan:

- Add `DeviceRepositoryPort.read_range(device_id, path, offset, length)` (ADB `exec-out dd …` or `tail -c +N | head -c M`).
- Add a loopback-only **ranged HTTP route** `GET /api/device/stream?…` that honours `Range`. This one route serves two consumers:
  - ffmpeg reads `-ss 1 -i http://127.0.0.1:<port>/api/device/stream?… -frames:v 1` for a thumbnail. It seeks to `moov` itself and fetches only a few MB.
  - The lightbox's `<video src>` gives in-browser playback, with seeking, and no full pull.
- Show duration on the tile (from ffprobe, using the same ranged source). Use a placeholder while it loads.
- Spike B0 checks the bytes transferred and the latency per thumbnail, plus playback smoothness over USB 2.
- Risks:
  - Range requests contend with transfers, so there must be a pause/yield policy.
  - The route must not be reachable from the LAN.
  - The passcode cookie does not matter for loopback.
- iPhone (AFC): ranged reads are plain file seeks on the ifuse mount. Expect them to be slower, so verify separately.

**B0 result (2026-10-20, Pixel 10a, Android 17, toybox 0.8.13).** Spike ran 12 clips (5 MB to 1.5 GB) through a loopback `adb exec-out dd` Range server. The phone had no WhatsApp or screen-recording clips, so the mix is 8 Camera, 1 DJI, 1 iPhone .MOV, 1 Download and 1 Movies clip. Scripts are in the session scratchpad only.

- **Codecs.** 10 of 12 clips are HEVC. The Pixel records 4K HEVC at about 42 Mbps (5.3 MB/s). 2 are H.264 (720p). 8 of 12 carry a -90 rotation tag. No AV1 or VP9 clips. 11 of 12 have `moov` at the tail (the H.264 clip is the exception).
- **Probe.** `ffprobe` over HTTP takes 0.2–0.5 s and reads 0.2–5 MB in 2–4 requests (a head read, a tail read for `moov`, then a few more).
- **Poster recipe.** `ffmpeg -ss 1 -i URL -frames:v 1 -vf scale=320:-2 -q:v 4`. It takes 0.8–1.6 s and reads 9–13 MB for 4K HEVC, whatever the file size. The reads are small head and tail ones, then one linear read of the first second of video (about 5 MB). Using `-ss 0` takes 0.6–0.9 s and reads about 4.5 MB, so prefer it. `-skip_frame nokey` did not help. ffmpeg auto-rotates, so portrait clips come out upright (320x568). Duration is read from the `Duration:` line in the same run's stderr, so one run gives both poster and duration (parse that line, no separate ffprobe).
- **Chunk cap.** A 4 MiB cap per response (206 with a truncated `Content-Range`) took 4–5 requests and about 1.0 s. A 1 MiB cap took 10–12 requests and about 1.4–1.6 s. Per-request `adb dd` latency to first byte is about 0.10 s, so more requests cost time. 4 MiB is the poster default.
- **Concurrency.** 4 parallel posters took 1.9–2.4 s, against 3.7–4.1 s sequentially, so use a cap of 2–4.
- **Playback throughput.** Sustained streaming with sequential Range reads gave 7.8 MB/s at a 1 MiB cap, 16 MB/s at 4 MiB and 24 MB/s at 16 MiB. That is 3x the bitrate of 4K HEVC (5.3 MB/s) at 4 MiB, and 4.5x at 16 MiB. Time to first byte after a seek into the middle was 0.10–0.12 s. **Raw transport is feasible.** A playback chunk cap of 8–16 MiB looks right.
- **Blocker for `<video src>`.** The bundled Qt WebEngine (PyQt6-WebEngine 6.11, no proprietary codecs) answers `canPlayType` with "no" for H.264 (avc1), HEVC (hvc1/hev1) and AAC. It says "probably" for AV1, VP9, VP8. Direct `<video>` playback of Pixel clips will not work in the desktop shell. It would need an on-the-fly ffmpeg transcode to VP9/WebM or fragmented AV1 (CPU cost for 4K HEVC, so scale down to 720p) or a poster-only phase B. The Range server is still needed as ffmpeg's source. Windows and macOS shells use the system WebView2/WKWebView, which play H.264 and HEVC, but that was not tested here.
- **Risks.** `dd` reads beyond what the client uses (a client abort can waste the rest of a chunk, so keep caps small). Each request spawns an `adb` process (about 0.1 s). A 4K HEVC poster costs about 10 MB of USB reads, so it must yield to transfers. Not tested: iPhone/AFC, HEVC on WebView2/WKWebView.

## Open questions for the user

- Should the picker get a grid view, or thumbnails inside list rows only (Phase A default)?
- Is a lightbox in Phase A fine, or thumbnails only first?
- Is it OK to keep the thumbnail cache across sessions (on disk, LRU)? The alternative is memory or temp only, for privacy.

## Phase B2 — video playback (later)

_Added 2026-10-20 after B0._ The Linux desktop shell (PyQt6-WebEngine 6.11) answers `canPlayType` "no" for H.264, HEVC and AAC, and "probably" only for AV1, VP9 and VP8. 10 of 12 sampled Pixel clips are HEVC. So `<video src>` on the loopback Range route cannot play phone clips in the app. Options to weigh in B2:

- **System player.** ▶ launches mpv or VLC, if installed, on the loopback Range URL. It streams, seeks and plays HEVC natively. It needs a player present and is Linux-first.
- **Live transcode.** ffmpeg transcodes to 720p VP9/WebM for an in-app `<video>`. It plays inside the app, but costs heavy CPU (4K HEVC decode plus VP9 encode), and every seek restarts the transcode.
- **Other shells.** WebView2 (Windows) and WKWebView (macOS) were not tested and may play H.264/HEVC natively.

B0 says the transport is ready: sustained 16 MB/s with a 4 MiB chunk cap (3× the 4K bitrate), 23.6 MB/s with 16 MiB, and 0.1 s to first byte on a seek.

## Phase C — RAW previews (after B)

_Added 2026-10-20._ RAW files (`dng`, and later vendor formats such as `cr2`, `cr3`, `nef`, `arw`, `orf`, `rw2`, `raf`) show the 📄 icon today. Phase A treats them as out of scope.

- **Source of the picture.** A RAW file usually embeds a JPEG preview. The A0 spike found a DNG with no thumbnail in the head read, but a 1280×960 `PreviewImage` at a known TIFF offset. Plan: read the TIFF/IFD headers from a head read, find the largest embedded JPEG (`PreviewImage` / `JpgFromRaw` / SubIFD JPEG), fetch only those bytes with Phase B's `read_range`, then auto-orient and resize with Magick as in Phase A.
- **No full decode.** Never demosaic the RAW file. If it has no embedded JPEG, keep the icon.
- **Reuse.** The same cache, routes (`/api/device/thumb`, `/preview`), concurrency cap and lightbox are used; only the domain classifier (`is_previewable_image`) and the embedded-preview extractor change. It depends on Phase B's `DeviceRepositoryPort.read_range`.
- **Spike C0.** Check which RAW formats the user's phones actually produce (Pixel: DNG), the preview sizes and offsets, and the bytes and time per thumbnail. Check orientation tags, because RAW previews are often stored unrotated.
- **Risks.** Vendor makernote quirks, and previews placed past the end of a head read (needs the range read). The parser handles untrusted bytes, so it needs bounded reads and fuzz-style tests, as the EXIF parser has.
