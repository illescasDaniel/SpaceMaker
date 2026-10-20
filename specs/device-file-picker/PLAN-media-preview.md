# Plan — media previews in the phone picker

_Drafted 2026-10-20. Status: plan only, no gate passed yet._ Lifts the "Thumbnails/previews of phone files" out-of-scope line in `SPEC.md`. Each phase below is its own SDD revision (Phase Gates 0→5), on its own worktree branch.

Phase A wireframe approved 2026-10-20; the SPEC.md "Photo previews" revision is drafted (awaiting approval).

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

## Open questions for the user

- Should the picker get a grid view, or thumbnails inside list rows only (Phase A default)?
- Is a lightbox in Phase A fine, or thumbnails only first?
- Is it OK to keep the thumbnail cache across sessions (on disk, LRU)? The alternative is memory or temp only, for privacy.
