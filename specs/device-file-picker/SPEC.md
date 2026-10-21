# Device file picker (in-app phone browser)

## Metadata

- **Feature:** An in-app screen that browses a USB-connected phone one directory at a time and returns picked folders/files to its caller. Replaces the adbfs FUSE mount + native OS dialog.
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-device-picker`; entry points `#btn-uft-add-files` / `#btn-uft-add-folder` in `#view-usb-file-transfer` and `#btn-wz-add-folder` / `#btn-wz-add-files` in the USB photo backup Step 1. **Wireframe approved** 2026-10-19 (iPhone uses the same picker; photo backup gets Add folder + Add files; adbfs removed).
- **Spec approved:** 2026-10-19 (original picker)
- **Revision — scroll pagination:** wireframe revision (auto-load sentinel, “Loading more…”, inline Retry, **Load more** fallback) approved 2026-10-19 (in chat); **spec revision approved** 2026-10-19 (in chat); "No match" rule amended 2026-10-19 (in chat: filter typed and `total` = 0). Plan: [PLAN-scroll-pagination.md](PLAN-scroll-pagination.md)
- **Revision — sorting:** wireframe revision (sortable **Name** / **Size** / **Modified** column headers with ▲/▼, toolbar **Sort** menu ≤ 520 px) approved 2026-10-19 (in chat); **spec revision approved** 2026-10-19 (in chat).
- **Revision — photo previews:** wireframe revision (thumbnails in image rows, 👁 button, lightbox; `wireframes/app.html`, `#view-device-picker`) **approved** 2026-10-20; **spec revision approved** 2026-10-20 (in chat). Plan: [PLAN-media-preview.md](PLAN-media-preview.md) (Phase A; videos are Phase B).
- **Revision — video posters (Phase B, posters only):** wireframe revision (video rows with poster + ▶ + duration badge, lightbox stepping through photos and videos, “Video previews” demo buttons; `wireframes/app.html`, `#view-device-picker`) **approved** 2026-10-20; **spec revision approved** 2026-10-20 (in chat). No in-app playback (Phase B2), no RAW (Phase C). Plan: [PLAN-media-preview.md](PLAN-media-preview.md).
- **Revision — grid view:** wireframe revision (View control Auto · List · Grid, grid tiles, per-folder choice, folder-type table; `wireframes/app.html` `#view-device-picker`) **approved** 2026-10-21 (in chat); **spec revision approved** 2026-10-21 (in chat). Plan: [PLAN-grid-view.md](PLAN-grid-view.md).
- **Revision — RAW previews (Phase C, DNG):** wireframe revision (RAW rows/tiles as photos with a bottom-left **RAW** badge, lightbox caption “RAW (DNG)” + embedded-preview note, “no embedded preview” error, “RAW previews” demo buttons; `wireframes/app.html` `#view-device-picker`) **approved** 2026-10-21 (in chat); **spec revision approved** 2026-10-21 (in chat); **amended** 2026-10-21 (in chat, after the real-phone check): BitsPerSample is checked only when held (tail-IFD0 Pixel files), iPhone example is `IMG_3809.DNG`. C0 spike numbers: [PLAN-media-preview.md](PLAN-media-preview.md) (“C0 result”).
- **Callers:** [usb-file-transfer](../usb-file-transfer/SPEC.md) (**Add more**), [extract-media](../extract-media/SPEC.md) / [main-wizard](../main-wizard/SPEC.md) Step 1 for ADB and iPhone USB (**Add more**)
- **Ports (planned):** outbound `DeviceRepositoryPort.list_directory(device_id, path) -> list[DeviceEntry]` (contract unchanged; adapters stay dumb); domain `DeviceEntry`, `DeviceDirectoryScrollPage` with an opaque keyset cursor; application-level `DeviceListingCache` (not a port) owned by the long-lived services object; photo previews add `DeviceRepositoryPort.read_head(device_id, path, max_bytes, timeout)`, a thumbnail-extraction port and a preview-cache port (names settled at the architecture gate); video posters add `DeviceRepositoryPort.read_range(device_id, path, offset, length, timeout)`, a video-poster port (ffmpeg) and an application-level short-lived stream-token registry (not a port)
- **Supersedes:** adbfs mount path in usb-file-transfer (“Mount backends”), `adbfs` in [packaging](../packaging/SPEC.md), `docs/legal/THIRD_PARTY_TOOLS.md`

## Design decisions

_Proposed — confirm or adjust at spec review._

| Decision | Answer |
|----------|--------|
| **Success criteria** | A user on Linux, macOS or Windows with an authorized Android phone can open the picker, navigate to any folder under user storage, tick several folders/files across several directories, and see them as removable sources in the calling screen — with no extra install, no FUSE, no native dialog. The picker is a module-screen feature: desktop app (or the computer running SpaceMaker) only, never other devices on the LAN (only QR/Wi-Fi transfer and gallery endpoints are LAN-visible). Picks are stored as device-relative paths (user-storage prefix stripped), identical to today’s Browse extras, so the existing transfer/extract pipelines and idempotency are unchanged. iPhone (AFC) lists through the same screen. |
| **Failure handling** | Per directory, the picker shows one of: loading, empty, permission denied (e.g. `Android/data` on Android 11+), device unauthorized, device unplugged/offline, listing timed out, generic error — each with Retry or Go up where it helps. Failures never clear ticked items. A failed **next-page** fetch keeps every loaded row and tick and shows an inline “Couldn’t load more items.” row with **Retry** at the bottom of the list (no full-panel error); an invalid or expired cursor is answered 400 `invalid_cursor` and the client silently restarts from page 1 (ticks kept). A failed listing leaves the previous directory’s selection and path intact. Closing the picker (Cancel) discards picks; Add returns them. Nothing is copied by the picker. |
| **Performance & resource budget** | One `adb shell` call (or one AFC directory read) per directory opened, plus one per explicit refresh (**Retry**) or cache expiry; never recurse; sub-folders of a ticked folder are not expanded in the picker. Results are served in pages of 100 entries (request `limit` bounded 1..500). The application layer holds a listing cache `DeviceListingCache`: TTL 30 s, LRU ≤ 8 directories, keyed `(method, device_id, path)`, errors are never cached, `refresh: true` bypasses it; later pages, filter changes, the hidden toggle and sort changes are served from the cached listing with no device call; a page served from the cache (sort + filter + slice of ~5 000 entries) answers in ≤ 50 ms. Filter and **Show hidden** are applied server-side over that listing — the client never downloads all pages to filter. The UI appends rows as pages arrive and never re-renders existing rows. Directory listing of ~5 000 entries returns the first page in ≤ 2 s on USB 2. The server holds no persistent connection. Entry payload ≤ ~150 bytes/entry (a 100-entry page ≈ 15 KB). Stale responses are dropped when the user navigates away, filters or toggles (request id); a superseded listing is not awaited. |
| **Trust boundary** | Untrusted input: the `path` sent by the web client (including a LAN client probing the endpoint) and file names returned by the phone (arbitrary unicode, spaces, quotes, newlines, `$`, backticks). The inbound route validates and normalizes `path` (no `..`, no NUL, no absolute escape, must resolve under the user-storage root) before the adapter runs; `cursor` is an opaque string decoded and validated server-side (malformed, tampered or not-a-cursor → 400 `invalid_cursor`, never reaches the adapter); `query` is a plain case-insensitive substring, length-bounded (≤ 200 chars, longer → 400), matched in Python over the cached listing and never sent to the device shell; `limit` is bounded 1..500 (out of range, or a `query` over 200 characters, is rejected by request validation with 422, not silently clamped), `sort` / `order` are closed enums (any other value → 422) and `show_hidden` / `refresh` are booleans; the stored sort preference is re-validated when read (unknown or corrupt → default **Name, A → Z**, never an error); the ADB adapter passes the path as a single `shlex`-quoted argument and never builds shell from phone-provided names. File names from the phone are rendered with `textContent` only. `POST /api/device/list` and the extras routes are loopback-only like every other module-screen API (403 `desktop-only` for LAN clients; the network-passcode gate still answers first when a passcode is set — [network-passcode](../network-passcode/SPEC.md)). The picker only lists; copying/moving remains in the transfer/extract use cases. |
| **Photo previews — success criteria** | Image rows show a thumbnail within ~0.5 s of becoming visible on a typical camera JPEG (A0 spike on a Pixel: 64 KB head read 0.04–0.10 s; 97% of camera JPEGs carry an EXIF thumbnail in the first 55 KB). The lightbox shows a large rendition (≤ 1600 px, fit-within) within ~1.5 s of opening, after showing the thumbnail at once. Formats: `jpg`, `jpeg`, `png`, `webp`, `gif`, `heic`, `heif`. HEIC/HEIF is decoded by the host Magick's libheif and **has not been verified on a real HEIC phone** (the spike phone has none) — to be checked during implementation. DNG: see **RAW previews** below; other RAW formats → icon only (out of scope). Videos: see **Video posters** below. Works for ADB and AFC. |
| **Photo previews — strategy** | **Thumbnail (320 px, JPEG):** (1) read the first 64 KB of the file; (2) if it holds an embedded EXIF/HEIC thumbnail, use it, applying the EXIF Orientation; (3) otherwise, **only if the file is ≤ 25 MB**, pull the whole file to a temp file and have Magick produce a 320 px fit-within JPEG (`-auto-orient`); (4) over 25 MB with no embedded thumbnail, or any failure → no preview, the UI keeps the icon. **Lightbox rendition (1600 px fit-within, JPEG):** full pull to a temp file + Magick, same 25 MB cap. Over the cap the lightbox shows the (upscaled) thumbnail if one exists plus the note “Full preview unavailable for files over 25 MB”; with no thumbnail either it shows the error state. Temp files are deleted in every outcome (success, error, timeout, cancel). |
| **Photo previews — failure handling** | A preview failure never affects the picker: the row keeps its icon with no error text, stays tickable, and the listing and ticks are untouched. Phone unplugged or read timeout → icon; the tile is retried the next time it becomes visible (folder reopened, or scrolled out and back), never on a timer. Device busy with a transfer/extract job → the row stays a plain icon (not marked failed) and is requested again on its next visibility. The lightbox shows “Preview unavailable” when the large rendition fails and stays usable (navigation, **Selected**, Esc). |
| **Photo previews — performance & resource budget** | At most **4** concurrent device reads per device (server-enforced; the client also keeps ≤ 4 requests in flight). Per-read timeouts: 10 s for the head read, 30 s for a full pull; Magick calls bounded by the same timeout. Previews are **not started** while a USB transfer or extract job is using the same device (409 `device_busy`) — a transfer always wins. Only rows currently visible request thumbnails (`IntersectionObserver`); requests are aborted on scroll-away, folder change and picker close; the lightbox requests only the current image (the thumbnail of a neighbour is already loaded as a row). **Disk cache** under the app cache directory (`device-thumbs/`, never the library, never the phone): key = hash(device id, path, size, mtime); one JPEG per key and kind (thumbnail / preview); a format-version marker in the directory name or a marker file (as for the gallery thumbnails) invalidates old entries when the pipeline changes; atomic writes (temp file + rename); LRU eviction keeps the cache ≤ **200 MB**; the cache survives restarts. A cache hit makes no device call and answers in ≤ 50 ms. |
| **Photo previews — trust boundary** | Untrusted input: `path`, `device_id`, `method`, `size`, `mtime` on the new routes, and the bytes of the image (arbitrary, possibly malformed). The routes are **loopback-only** (`require_loopback` → 403 `desktop-only`; passcode gate first) and are **not** added to `LAN_ALLOWED_ROUTES`, so the [lan-access](../lan-access/SPEC.md) default-deny holds (its route table gains these two rows as **Desktop**). `path` is validated and normalized exactly as for `/api/device/list` (no `..`, no NUL, under user storage) before any adapter runs; the ADB adapter passes it as one `shlex`-quoted argument. `size` and `mtime` come from the client listing but only form part of the cache key: a wrong value just causes a cache miss and regeneration, never access to another file; the server compares `size` with the real file size before choosing the 25 MB path. Image decoding runs in a subprocess (Magick) with a timeout and a resource limit on pixel dimensions; the output is always re-encoded JPEG, so original bytes are never served. Preview bytes are written only to the cache directory and temp files, **never into the user's library**. Responses use `Cache-Control: private, max-age=300, must-revalidate` with a strong `ETag` and answer 304 on `If-None-Match`, consistent with `/thumbs`. |
| **Video posters — success criteria** | Video rows show a **poster** (the first frame) with a small ▶ glyph and a duration badge. A poster appears within ~1.5 s of the row becoming visible (B0 spike, Pixel 10a, 4K HEVC: 0.6–0.9 s, ~4.5 MB read regardless of file size); 4 in parallel ≈ 2.4 s; the lightbox large frame within ~2 s. Formats (case-insensitive): `mp4`, `mov`, `m4v`, `3gp`, `mkv`, `webm`. **Posters only — there is no playback in the app** (the bundled Qt WebEngine cannot decode H.264/HEVC/AAC, B0); playback is Phase B2. RAW is Phase C. The same endpoints as photos serve videos. Works for ADB and AFC. |
| **Video posters — strategy** | **Poster = the first frame** (`ffmpeg -frames:v 1`, rotation applied so portrait clips come out upright), scaled fit-within to 320 px (`thumb`) or 1600 px (`preview`), JPEG. **Duration** comes from the same ffmpeg run (stderr `Duration:` line) — no separate ffprobe. ffmpeg reads the phone file through a **loopback-only internal stream route** `GET /api/device/stream?token=…` (a single `Range`, ≤ 4 MiB per response) which reads through `DeviceRepositoryPort.read_range` (ADB `exec-out dd iflag=skip_bytes,count_bytes`, `shlex`-quoted; AFC seek + read on the mount). 4 MiB is the cap because B0 measured ≈ 1.0 s per poster at 4 MiB against ≈ 1.5 s at 1 MiB (per-request `adb` latency ~0.1 s). The file is never pulled whole, so videos have **no size cap** (no `too_large`). The cache stores the JPEG **and** the duration; the cache format version is bumped, so existing photo-only entries are a miss. |
| **Video posters — failure handling** | Same as photos: a failure never affects the picker; the row keeps its 🎞 icon with **no badge** and no error text, stays tickable, and is retried only when it becomes visible again. No poster (undecodable, no video stream, ffmpeg timeout, unplugged) → 🎞 and no duration badge. A transfer/extract job → 409 `device_busy` **before** starting; if one starts mid-run the stream route answers 409, ffmpeg fails and the poster fails as `device_busy` (row stays a plain icon, nothing cached). Errors are never cached. The lightbox shows “Video unavailable” when the large frame fails and stays usable (navigation, **Selected**, Esc). |
| **Video posters — performance & resource budget** | One video poster holds **1 of the same 4 per-device slots** as photos for its whole ffmpeg run; the stream route and ffmpeg's sub-requests take **no extra** slots (they are covered by the token). ffmpeg runs with `-protocol_whitelist http,tcp`, the only input URL `http://127.0.0.1:<port>/api/device/stream?token=…`, a **20 s** timeout, and is killed on timeout, client abort or picker close. A stream response carries ≤ **4 MiB**. ~4.5 MB (4K HEVC) is read per poster whatever the file size. Disk cache: the existing `device-thumbs/` LRU, ≤ **200 MB**, same key fields (device id, path, size, mtime) plus kind; a hit makes no device call and answers in ≤ 50 ms. Previews yield to transfers/extracts. |
| **Video posters — trust boundary** | Untrusted: the stream `token`, the `Range` header, the video `path`/`size`/`mtime` on thumb/preview, and **every byte ffmpeg parses**. The stream route is **loopback-only** (`require_loopback` → 403 `desktop-only`; passcode gate first), **never on `LAN_ALLOWED_ROUTES`**, and is not a general phone-file reader: the use case mints a random **128-bit token** bound to (method, device_id, normalized path, size) only for the duration of one poster generation and **revokes it afterwards**; an unknown, expired or revoked token → 404, and the route can read nothing but the one file the token names. `path` is validated and normalized exactly as for `/api/device/list` before the token is minted; ADB passes it as one `shlex`-quoted argument. The stream route validates `Range` strictly (a single `bytes=a-b` or `a-`; anything else → 400/416) and never reads past the bound `size`. ffmpeg is the only process that sees the URL, runs with a protocol whitelist and a timeout, and its output is always re-encoded JPEG — original bytes are never served and never written to the library or the phone. [lan-access](../lan-access/SPEC.md)'s route table gains one row, `GET /api/device/stream` → **Desktop**. |
| **Grid view — success criteria** | The picker can show a folder as **List** (today's rows) or **Grid** (square tiles). The layout is resolved in this order: **the user's choice for this folder → the folder type → auto-detection** (see **Grid view**). Opening `DCIM/Camera`, a `Screenshots` folder or anything under `Pictures` shows a Grid with no click; `Documents` and `Download` (and anything under them) show a List; an untyped folder is a Grid when it holds at least one photo/video and they are at least 60 % of its visible entries. Pressing **List** or **Grid** is remembered **for that folder only** and honoured on every later open, across app restarts and for every device; pressing **Auto** forgets it. Filter, sort and **Show hidden** never flip the layout. Switching the mode keeps every tick and the loaded rows. Works for ADB and AFC. |
| **Grid view — failure handling** | A corrupt stored map, or one bad entry in it (unknown view value, bad or non-normalized key), is ignored **entry by entry** and never produces an error (the folder resolves as if nothing were stored). A failed write of the choice (disk error) keeps the chosen mode for the rest of the session and shows no error: the client remembers every choice made in this picker session per folder, and that session choice wins over a `stored_view` that is missing or stale; after an app restart the folder falls back to the resolution order. A listing that fails (unplugged, unauthorized, permission denied, timeout, generic error) shows the same state panels in **both** layouts, and the View control stays usable. No count, type or stored value can make the listing itself fail. |
| **Grid view — performance & resource budget** | `entry_count` and `media_count` are computed over the **cached listing** (hidden rule applied, `query` ignored): no device call, within the existing ≤ 50 ms budget for a cached page of ~5 000 entries. The folder type is resolved from the normalized path alone (a table lookup, **no listing**). A mode switch **re-renders the already-loaded rows** in the other layout with no request, keeps the ticks and the scroll position at the first visible item where possible, and keeps in-flight thumbnail requests and already-loaded thumbnails where the DOM allows (a request whose row is rebuilt is not restarted needlessly). Grid tiles use the **same 320 px thumbnails and video posters**, the same **≤ 4 in flight** per device and the same `IntersectionObserver` lifecycle as rows; no new device read is introduced. The `device_picker_views` map holds **≤ 500** folders (LRU); a view write is one small preference write and no device call. |
| **Grid view — trust boundary** | Untrusted input: the `view` and `path` of the new route and the stored map in the preferences file. `view` is a **closed enum** (`auto` \| `list` \| `grid`; anything else → 422). `path` is validated and normalized **exactly as for `/api/device/list`** (no `..`, no NUL, under user storage; 400 `invalid_path`) before it is used as a key; stored keys are **re-validated on read** and an invalid key or value is dropped. Folder names (from the phone) used for the folder-type match are only compared, never executed or interpolated, and every name is rendered with `textContent`. `PUT /api/device/view` is **loopback-only** (`require_loopback` → 403 `desktop-only`; the network-passcode gate answers first) and is **not** on `LAN_ALLOWED_ROUTES`; [lan-access](../lan-access/SPEC.md)'s route table gains one row, `PUT /api/device/view` → **Desktop**. The route makes no device call and writes only the preference file. |
| **RAW previews — success criteria** | Rows for `.dng` files (case-insensitive: Pixel `….RAW-02.ORIGINAL.dng`, iPhone ProRAW `IMG_….DNG`) show a thumbnail and open in the lightbox like photos. The picture is the **JPEG preview embedded in the DNG**; the RAW data is never decoded or demosaiced. Thumbnail within ~0.5 s of becoming visible for a Pixel DNG and ~0.8 s for an iPhone ProRAW DNG (C0 spike, Pixel 10a: 2–3 small reads of ~0.1 s each, then the preview range read 0.08–0.13 s for Pixel's 1280×960 / 170–550 KB preview and 0.19–0.31 s for iPhone's 3088×2316–4032×3024 / 1.7–4.0 MB preview; Magick 25–200 ms); lightbox large rendition within ~1.5 s. The large rendition is ≤ 1600 px fit-within and **never upscaled** (a Pixel DNG's lightbox picture is at most 1280 px). Output is upright for every EXIF Orientation (spike saw 1, 6, 8). A `.dng` that is really a JPEG (Snapseed saves its edits as JPEG bytes with a `.dng` name) is previewed exactly as a JPEG. Works for ADB and AFC through the same routes. |
| **RAW previews — strategy** | Content decides, not the extension: (1) read the first **4 KB** (`read_range(0, 4096)`). (2) Bytes start with `FF D8` → it is a JPEG: run the **Photo previews** strategy unchanged (EXIF thumbnail from the head, else the ≤ 25 MB full pull). (3) Bytes start with a TIFF header (`II*\0` or `MM\0*`) → parse the **IFD0** entry table; if IFD0 lies beyond the bytes held (5 of 9 Pixel originals keep IFD0 near the end of the file), read 4 KB at the IFD0 offset. (4) **Candidates** are IFDs describing a displayable JPEG: Photometric = 6 (YCbCr), BitsPerSample 8 (checked only when its values lie in the bytes already read — on tail-IFD0 Pixel files the three values sit ~1.77 MB away and are **not fetched**; the `FF D8` check and the Magick decode still guard), Compression 6 or 7, NewSubfileType 0 or 1, and either a single strip (StripOffsets/StripByteCounts) or JPEGInterchangeFormat/Length. IFD0 is checked first (it is the preview on both Pixel and iPhone); only when IFD0 is not a candidate are the SubIFDs (tag 0x014A) read, one 4 KB read each. Raw tiles (Photometric 32803 CFA / 34892 LinearRaw), semantic masks (NewSubfileType 65540) and JPEG XL tiles (Compression 52546) are never candidates. (5) **Pick** the largest candidate whose long edge is ≤ 1600 px, else the smallest larger one; the same JPEG serves `thumb` (320 px) and `preview` (1600 px). (6) Range-read exactly that JPEG and check it starts with `FF D8`. (7) Magick resizes and re-encodes: if the preview JPEG carries its own EXIF Orientation, `-auto-orient` applies it (iPhone); otherwise the DNG's IFD0 Orientation is applied (Pixel previews have no EXIF and are stored unrotated) — **never both**. No EXIF is written anywhere. (8) Neither JPEG nor TIFF, no candidate, or Magick cannot decode it → no preview (404). A TIFF DNG is never fully pulled, so it has **no 25 MB cap** and never answers 413. |
| **RAW previews — failure handling** | Same as photos: the row keeps the 🖼 glyph with no error text and no RAW badge, stays tickable, and the listing and ticks are untouched; unplugged/timeout → retried on next visibility; device busy → plain icon, retried on next visibility. In the lightbox, 404 `no_preview` on a `.dng` shows “Preview unavailable — This RAW file has no embedded preview the app can show. You can still select this file.”; every other failure shows the photo error text. Lightroom `…_proxy.dng` files (JPEG XL tiles, no JPEG) are the known no-preview case. |
| **RAW previews — performance & resource budget** | A RAW preview holds **1 of the same 4 per-device slots** for its whole extraction (all reads + Magick), and yields to transfers/extracts exactly as photos (409 `device_busy`, not started while a job uses the device). Device reads per uncached request: 1–2 header reads (4 KB each) + at most **8** SubIFD reads (only when IFD0 is not the preview) + 1 preview read; bytes read ≈ preview size + ≤ 40 KB. Timeouts: 10 s for each header read, 30 s for the preview read, Magick bounded as for photos. The extracted JPEG lives only in memory or a temp file deleted in every outcome; only the resized output is cached, in the same `device-thumbs/` cache with the same key, LRU and 200 MB budget (no cache format bump: `.dng` was never cached before). |
| **RAW previews — trust boundary** | The DNG bytes are **untrusted** and parsed in pure Python by a bounded parser: at most **64** entries per IFD, at most **8** SubIFDs, no IFD visited twice, every offset and length checked against the bytes held and the real file size before any read, the preview length capped at **8 MB**, and any malformed structure → no preview (never an exception escaping as 500). The parser is covered by fuzz-style tests (truncated headers, cycles, huge counts, out-of-range offsets, both byte orders). Routes, path validation, loopback-only rule, `size`/`mtime` handling, Magick limits, re-encoding and “never into the library or onto the phone” are unchanged from **Photo previews — trust boundary**. |

## Triggers & routing

- **Open:** from a caller button; the SPA navigates to `#view-device-picker` with a caller context `{ origin, kind: "files" | "folders" | "both", method: "adb" | "afc", mediaOnly }`. Opening does not start a server-side session; each directory read is one stateless request.
- **Breadcrumb:** `Home / <origin module> / Pick folders` (or `Pick files`, or `Pick files or folders` for `kind: "both"`). The origin crumb returns to the caller without picks.
- **API (inbound, JSON):** `POST /api/device/list` with `{ method, device_id, path, cursor?: string | null, limit?: int, query?: string, show_hidden?: bool, refresh?: bool, sort?: "name" | "mtime" | "size", order?: "asc" | "desc" }` → `{ path, entries: [{ name, is_dir, size, mtime }], next_cursor: string | null, total, total_unfiltered, sort, order, error? }`. `path` is storage-relative (`""` = **Phone storage** root = `/sdcard` canonical). `limit` defaults to 100 (bounded 1..500); `show_hidden` defaults to false; `refresh` defaults to false and bypasses the listing cache. Entries are ordered by the effective sort (see **Sorting** below; default folders first, then case-insensitive name A → Z, ties broken by exact name). `sort` and `order` must be sent together or not at all (one without the other → 422); when omitted, the stored picker sort preference is used. The response always echoes the effective `sort` / `order`. `total` is the count after `query` / `show_hidden` filtering; `total_unfiltered` is the directory’s full count. `next_cursor` is `null` on the last page. The cursor is **keyset**: it encodes the effective `sort` / `order` and the sort key of the last returned entry, so continuing after the cache expired and the folder changed on the phone neither skips nor duplicates entries. `show_hidden` moves hidden (dot) filtering to the server — before this revision the client filtered; hidden entries are excluded from pages, `total` and `next_cursor` unless `show_hidden` is true. An invalid cursor — including a cursor issued under a different `sort` / `order` than the request’s, or one issued before this revision — returns 400 `invalid_cursor`.
- **Return:** on **Add N items** the SPA hands the ticked `[{ path, is_dir }]` to the caller; the caller posts them with its existing extras endpoint (`set_usb_transfer_extra_paths` for USB file transfer; a new equivalent for extract extras).
- **Methods:** ADB (all OS). AFC (Linux, same as today): `list_directory` reads one directory under the ifuse mount owned by the session. Root for AFC is the device root (**iPhone**), typically only `DCIM`.

## Photo previews — API

Two loopback-only `GET` routes, `image/jpeg` on success. Query: `method` (`adb` | `afc`), `device_id`, `path` (storage-relative, as in `/api/device/list`), `size` (int ≥ 0), `mtime` (int ≥ 0).

| Route | Returns | Notes |
|---|---|---|
| `GET /api/device/thumb` | 320 px fit-within JPEG | Head-read strategy first, then the ≤ 25 MB full-pull fallback |
| `GET /api/device/preview` | 1600 px fit-within JPEG | Full pull, ≤ 25 MB |

Errors (JSON `{ "detail": <code> }`; the UI treats every non-2xx as “keep the icon” / “Preview unavailable”):

| Status | `detail` | Meaning |
|---|---|---|
| 400 | `invalid_path` | Path validation failed, unknown `method`, empty `device_id`, or AFC off Linux (same checks as `/api/device/list`); no device process started |
| 403 | `desktop-only` | Non-loopback client |
| 404 | `no_preview` | Not an image or video type, not a file, missing on the phone, or undecodable |
| 409 | `device_busy` | A transfer/extract job is using this device |
| 413 | `too_large` | Over 25 MB and no embedded thumbnail (`thumb`), or over 25 MB (`preview`) |
| 422 | — | `size` / `mtime` missing or negative (request validation) |
| 503 | `unplugged` / `timeout` / `unauthorized` | Device unavailable or a read exceeded its timeout |

Identification of the device matches `/api/device/list`: `method` + `device_id` (the id the picker already holds); the route resolves the adapter the same way. For `preview`, a file over 25 MB returns 413 and the lightbox falls back to the already-loaded thumbnail (see Visual rules). Classification of image extensions lives server-side (the TS list is only a UI hint for showing the placeholder). `dng` is a previewable image extension: a `.dng` request follows the **RAW previews — strategy** (no 413 for a TIFF DNG; a `.dng` that is really a JPEG follows the photo rules, including 413).

## Video posters — API

`GET /api/device/thumb` and `GET /api/device/preview` (above) **also accept video paths** (`mp4`, `mov`, `m4v`, `3gp`, `mkv`, `webm`, case-insensitive): same query, same JPEG output (320 px / ≤ 1600 px fit-within), same `ETag` / 304 / `Cache-Control: private, max-age=300, must-revalidate`, same error codes — except that a video is **never** 413 `too_large`. A response for a video carries `X-Media-Duration: <seconds, decimal>` (e.g. `42.37`) on **200 and on 304** when the duration is known, and omits the header when it is unknown. Stored `X-Media-Duration` is part of the cache entry.

Internal route (loopback-only, used by the poster's own ffmpeg, never by the web client):

| Route | Returns | Notes |
|---|---|---|
| `GET /api/device/stream?token=…` | `206` with `Content-Range`, `Accept-Ranges: bytes`, `application/octet-stream`, ≤ 4 MiB | Requires a single `Range: bytes=a-b` or `bytes=a-` |

| Status | `detail` | Meaning |
|---|---|---|
| 206 | — | The requested range, truncated to 4 MiB (`Content-Range` states the bytes actually sent) |
| 400 | `range_required` | No `Range` header (a 206 of the first chunk is **not** allowed) or a malformed / multi-range header |
| 403 | `desktop-only` | Non-loopback client |
| 404 | `unknown_token` | Token unknown, expired or revoked |
| 409 | `device_busy` | A transfer/extract job started while the poster was being generated |
| 416 | `range_not_satisfiable` | `a` is at or past the bound `size` (`Content-Range: bytes */<size>`) |
| 503 | `unplugged` / `timeout` / `unauthorized` | Device unavailable or the range read exceeded its timeout |

The token is minted by the use case, not by any route: no HTTP route returns, lists or accepts the creation of a token.

## Grid view — API

**`POST /api/device/list` (additions).** The **first page** of a listing (request without `cursor`, including every filter / hidden / sort restart) additionally returns:

| Field | Type | Meaning |
|---|---|---|
| `entry_count` | int | Entries in the folder after the hidden rule (`show_hidden`), **ignoring `query`**: folders + files |
| `media_count` | int | Of those, files whose extension is a photo or video type (the sets of **Photo previews** and **Video posters**, case-insensitive); folders never count |
| `folder_view` | `"grid"` \| `"list"` \| `null` | The layout the **folder-type table** gives for `path` (`null` = no ancestor-or-self matches) |
| `stored_view` | `"list"` \| `"grid"` \| `null` | The user's stored choice for exactly this `path`; `null` = Auto |

- `entry_count` and `media_count` come from the cached listing and cost no device call; they are **omitted** from error responses. `folder_view` and `stored_view` need no listing and are present on page 1 **also when the listing fails**, so the View control can render in every state: a listing error (`DeviceBrowseError`, body `{"detail": {"error", "message"}}`) carries them inside `detail` (`detail.folder_view`, `detail.stored_view`); an invalid `path` (400 `invalid_path`) carries neither.
- Pages after the first (a request with `cursor`) **omit all four fields**; the client keeps the values from page 1 of the current open.
- The response shape otherwise does not change; clients that ignore the new fields behave as before.
- The **media extension set** and the **folder-type table** live in the **domain** and are the single source for the server and (via these fields) the client; the TS extension list stays a placeholder hint only.

**`PUT /api/device/view`** (new, loopback-only). Body `{ "path": string, "view": "auto" | "list" | "grid" }`.

| Status | Meaning |
|---|---|
| 204 | Stored (`list` / `grid` sets or overwrites the entry for `path`; `auto` deletes it, and deleting a missing entry is also 204). Makes no device call and does not check that the folder exists |
| 400 | `invalid_path` — path validation failed (same checks as `/api/device/list`) |
| 403 | `desktop-only` — non-loopback client (the passcode gate answers first) |
| 422 | `view` is not one of the three values, or the body is malformed |

**Persistence.** User preferences key `device_picker_views`: a map from the normalized **device-relative path** (`""` is the storage root) to `"list"` | `"grid"`; **shared by every device and both methods**. At most **500** entries, **LRU**: a set (create or overwrite) makes the entry the most recent, reads never refresh it, and adding the 501st drops the least recently set entry. Reading re-validates each key and value and drops bad ones (a key is kept only if it is already normalized, i.e. `normalize_browse_path(key) == key`; `/sdcard/DCIM` or `a/../b` is dropped, not rewritten; a value other than `list` / `grid`, including `auto`, is dropped). Settings → **Clear preferences** empties it, like `device_picker_sort`. The map is written only by `PUT /api/device/view`; `POST /api/device/list` never writes it.

## Visual & UI rules (aligned with wireframe)

- Header card: **Phone storage** (or **iPhone**) title + ⓘ; friendly device status line (never raw serials); optional media-only note when `mediaOnly`.
- Path trail (clickable crumbs, root shown as **Phone storage** — reuse `strip_android_user_storage_prefix` naming, never `/sdcard`, `storage/emulated/0` or `storage/self/primary`).
- Toolbar: **↑ Up** (disabled at root), **Select this folder** (hidden for `kind: "files"`, disabled at root), name **filter**, **Show hidden** toggle (off by default; dot-entries dimmed when shown).
- List: header row Name / Size / Modified — each header is a sort button (see **Sorting**): the active column shows ▲ (ascending) or ▼ (descending), the others no arrow; checkbox per row; folder name is a button that opens the folder (checkbox only selects); file rows are not links; in `kind: "folders"` file rows are visible but their checkbox is disabled; in `mediaOnly` non-media files are dimmed. Size `—` for folders. Modified column hidden at ≤ 520 px; at that width the toolbar shows a **Sort** menu (`<select>`) with six options — Name, A → Z · Name, Z → A · Newest first · Oldest first · Largest first · Smallest first — kept in sync with the headers (hidden above 520 px).
- Pagination: the next 100 rows load automatically when the end of the list nears the viewport (an `IntersectionObserver` sentinel is the last list item). While a page is in flight the list ends with a “Loading more…” row (spinner static under `prefers-reduced-motion`, `role="status"`). A footer inside the list reads “Showing N of M items” (M = filtered total) with a **Load more** button — the keyboard / no-`IntersectionObserver` fallback, disabled while a page is loading; the footer is hidden when everything is loaded. A failed next page replaces the “Loading more…” row with “Couldn’t load more items.” + **Retry** (`role="alert"`); loaded rows and ticks stay.
- States replace the list: loading spinner, empty, no filter match, permission denied (**Go up**), unauthorized (**Retry**), unplugged (**Retry**, ticked items kept).
- Sticky footer: selected count (`aria-live`), **Cancel**, **Add N items** (disabled at 0). Selection persists across folders within one picker session.
- Hint under the list when a folder is ticked: ticked folders are added whole, sub-folders included, when the job starts.
- Theme: system light/dark (`theme.css`); no motion beyond the existing screen fade (spinner static under `prefers-reduced-motion`). Mobile width: no horizontal page scroll.
- Entry points (revised 2026-10-20, wireframe approved): USB file transfer and USB photo backup Step 1 each have **one** accent-outlined **Add more (files or folders)** button (replacing the former **Add files…** / **Add folder…** pair) that opens the picker with `kind: "both"` — every row has an enabled checkbox and **Select this folder** is visible. In USB file transfer it sits directly under the preset checklist, above the extras list; the unavailable hint reads “Add more needs a connected, authorized device.” USB photo backup Step 1 (ADB / iPhone only; hidden for Wi‑Fi) has an extras list + **Add more** + ⓘ under the preset checklist, with the “only photos and videos are extracted” note.
- **Photo previews — rows:** image rows (`jpg`, `jpeg`, `png`, `webp`, `gif`, `heic`, `heif`) replace the 📄 icon with a 44 px rounded `object-fit: cover` thumbnail (36 px at ≤ 520 px). States: shimmer while loading (static under `prefers-reduced-motion`); the photo once loaded; the 🖼 glyph when the request fails or the file is too large — no error text in the row. The thumbnail is a `<button>` with `aria-label="Preview <name>"` and the visible **👁 Preview** button (also `aria-label="Preview <name>"`) is a second, keyboard-reachable opener; clicking anywhere else on the row behaves as before (checkbox selects, folder name opens). Videos get a poster (see **Video posters — rows**); other files show 📄, folders 📁, and neither requests a preview. Rows keep their checkbox in every state.
- **Photo previews — lightbox:** `role="dialog"` `aria-modal="true"` labelled by the file name; shows the photo fitted to the window, name, size, modified date, “n / N” (n among the **image and video rows of the loaded pages**, in list order; announced via `aria-live="polite"`), **←** / **→** buttons and arrow keys (disabled at the ends, no wrap), **Esc** and **✕** to close, and a **Selected** checkbox that mirrors the row's tick in both directions (in `kind: "folders"` mode, where file checkboxes are disabled, it is disabled too). Loading state: the blurred, upscaled thumbnail with a spinner (static under reduced motion), crossfading to the large rendition. Error state: “Preview unavailable” (and, for files over 25 MB, “Full preview unavailable for files over 25 MB” above the upscaled thumbnail); the file stays selectable. Focus is trapped inside; closing returns focus to the opener (thumbnail or 👁 button). Below 520 px the lightbox is full-screen with the ←/→ buttons in a bottom bar. Opening or stepping the lightbox does not change the list scroll position or the ticks.
- **Video posters — rows:** video rows (`mp4`, `mov`, `m4v`, `3gp`, `mkv`, `webm`) use the same rounded thumbnail button as photos (44 px, 36 px at ≤ 520 px) with the poster, a small ▶ glyph centred and a **duration badge** bottom-right: `m:ss` (`0:42`, `12:07`) and `h:mm:ss` from one hour (`1:02:15`). States: shimmer while loading (no ▶ or badge yet; static under `prefers-reduced-motion`); poster + ▶ + badge once loaded; the 🎞 icon alone, **no badge**, when there is no poster (failure, undecodable, unknown duration is shown as a poster with ▶ and no badge). The thumbnail button and **👁 Preview** carry `aria-label="Preview <name> (video, <duration>)"` (duration omitted when unknown). No error text in the row; the checkbox works in every state.
- **Video posters — lightbox:** the lightbox steps through **photos and videos together** (“3 / 58” counts both; arrow-key and button behaviour as for photos). A video shows its large frame (the poster first, blurred and upscaled with a spinner, then the ≤ 1600 px frame), the caption “Video · 0:42 · 86.0 MB · <date>” (duration omitted when unknown), and the muted note “Playback isn’t available in the app yet. Transfer the video to watch it.” There is no play button and no player. Hint: “← → to browse · Esc to close”. Error: “Video unavailable — The phone was unplugged or didn’t respond. You can still select this file.” Selected, Esc, focus trap and the ≤ 520 px full-screen layout are unchanged.
- **Grid view — toolbar:** the toolbar gets a **View** control: a three-button segmented control `role="radiogroup"` labelled **View** with `role="radio"` + `aria-checked` buttons **Auto · List · Grid** (one tab stop, arrow keys move and select, wrapping). Next to it: while **Auto** is selected, the note `#dp-view-auto-note` states what Auto resolved to (**Auto · Grid (photo folder)** / **Auto · List (documents folder)** when the folder type decided, **Auto · Grid** / **Auto · List** when detection decided); while **List** or **Grid** is selected (a stored choice), the hint `#dp-view-scope` reads **Only this folder** (it replaces the auto-note and tells the user the choice is not global; **Auto** forgets it). In grid, the Name / Size / Modified header is hidden and the toolbar **Sort** menu is shown at **every** width (it is still hidden above 520 px in List).
- **RAW previews — rows and tiles:** `.dng` rows and grid tiles are photos in every respect (thumbnail button, 👁, shimmer, 🖼 fallback, lightbox stepping, counted as media for Auto view). A loaded `.dng` thumbnail carries a small **RAW** badge bottom-left (hidden while loading and on failure; videos keep their duration bottom-right); the badge follows the extension, so a JPEG saved as `.dng` also shows it. The thumbnail and 👁 carry `aria-label="Preview <name> (RAW)"`.
- **RAW previews — lightbox:** caption “RAW (DNG) · 24.6 MB · <date>” and the muted note “This is the preview the camera saved inside the RAW file. The RAW data itself isn’t developed here.” under the picture (hidden in the error state). Error text as in **RAW previews — failure handling**. Navigation, Selected, Esc, focus trap and the ≤ 520 px layout unchanged.
- **Grid view — tiles:** see **Grid view** below. Photos, videos and the loaded/failed states reuse the **Photo previews** and **Video posters** rules (shimmer, 🖼 / 🎞 fallback with no error text, ▶ and duration badge); a tile never shows error text.

## Behaviour details

- **Restart semantics:** opening a folder (or Up / breadcrumb) starts at page 1 with the full-panel loading state and clears the filter. Typing in the filter restarts at page 1 after a 200 ms debounce (one request carrying `query`); toggling **Show hidden** or changing the sort restarts immediately (a pending filter debounce is folded into that one request). On filter/toggle/sort restarts the existing list stays visible but dimmed until page 1 arrives (no full-panel spinner), then is replaced and scrolled to top. Ticks are keyed by path and survive every restart. Any restart supersedes in-flight requests (request id) — their responses are dropped. When a filter is typed and `total` = 0 the **No match** state shows; otherwise a page with no rows shows the **empty** state (e.g. a folder holding only hidden entries while **Show hidden** is off).
- **Sort persistence:** the picker opens with the remembered sort (one value for every picker caller, ADB and iPhone alike) and keeps it while navigating folders (unlike the filter, opening a folder does not reset the sort). When a list request carries an explicit `sort` / `order` that differs from the stored preference, the server stores it in the user preferences (`device_picker_sort`) after the listing succeeds; requests without them never write. Settings → **Clear preferences** resets it to **Name, A → Z**.
- **Selected set:** keyed by storage-relative path. Ticking a folder and one of its descendants keeps both; the caller’s `merge_extra_paths` dedupes (parent wins).
- **Select this folder** adds the current directory as a whole-folder pick and refreshes the row/ footer state.
- **Photo backup extras:** the extract job queue = preset folders ∪ extras, filtered to media extensions (same filter as `list_media_paths`); destination stays `originals/` with stable relative paths. **Start extract** is enabled when ≥ 1 preset **or** ≥ 1 extra is selected. Extras are cleared on method change, Home exit, and library-root change, like USB file transfer extras.
- **Preset exist-probe** (USB file transfer): becomes one `list_directory("")` call — a preset shows only if a top-level directory of that name is in the listing. No FUSE walk. The probe goes through the same listing cache (so it and a picker open of the root within 30 s cost one device call between them) and requests `limit` 500 so a root with more than 100 folders is not truncated.
- **Hidden entries:** `.thumbnails`, `.nomedia`, etc. are kept in the cached listing but filtered out server-side by default (`show_hidden: false`); `SKIPPED_LIBRARY_DIR_NAMES` still apply when expanding ticked folders.
- **Android listing command:** implementation-defined (adapter picks the most robust of `toybox stat`/`find -printf`/`ls -la` with fallback for old Android), but must be NUL- or otherwise unambiguously delimited so names with spaces/newlines parse correctly, and must return size and mtime. Symlinks resolve to their target type when cheap; otherwise are listed as files.
- **Device gone mid-browse:** next list request returns `error: "unplugged"`; the UI shows the unplugged state; Retry re-runs the same directory.
- **Photo previews — request lifecycle:** a row requests its thumbnail only when it enters the viewport (with a small root margin); the request is aborted when the row leaves, the folder changes, a restart (filter / hidden / sort) replaces the rows, or the picker closes. At most 4 requests are in flight; the rest queue and are dropped with their rows. A thumbnail `src` carries the row's `size` and `mtime`, so an entry whose size or mtime changed is a new cache key. The lightbox requests `/api/device/preview` for the current image only, and aborts it when stepping or closing.
- **Photo previews — busy device:** while a transfer/extract job uses the device, `409 device_busy` leaves the row as a plain icon (not failed); it is re-requested the next time the row becomes visible (including after the folder is reopened). No polling.
- **AFC (iPhone):** the same routes read from the ifuse mount; the “head read” is a bounded file read of the first 64 KB. Same limits, timeouts and cache.
- **Video posters — request lifecycle:** rows request posters exactly like photos (visible rows only, aborted on scroll-away / folder change / restart / picker close, ≤ 4 client requests in flight shared with photos). The use case generates a poster as: check the cache (hit → return, no device call) → reserve one device slot → mint a stream token → run ffmpeg against the stream URL → read duration from stderr → store JPEG + duration → revoke the token (in a `finally`, in every outcome) → release the slot. A client abort kills ffmpeg and revokes the token.
- **Video posters — busy device:** `409 device_busy` leaves the row a plain icon (not failed) and it is requested again on its next visibility; a transfer/extract starting mid-run makes the stream route answer 409, the poster fails as `device_busy`, nothing is cached.
- **Video posters — AFC (iPhone):** the same routes; `read_range` is a seek + bounded read on the ifuse mount. Same limits, timeouts, 4 MiB cap and cache.
- **Grid view — preference:** the picker opens each folder in the layout from the resolution order (see **Grid view**); `stored_view` and `folder_view` arrive on page 1. Pressing **List** or **Grid** sets the layout at once and then sends `PUT /api/device/view` for the current folder (fire-and-forget; failure ignored, no error shown); pressing **Auto** sends `view: "auto"` and re-resolves from `folder_view` and the counts of the loaded page-1 response (no new list request). Navigating to another folder re-resolves; going back to a folder re-reads its stored choice from its own page 1.
- **Grid view — once per open:** the layout is decided when page 1 of an **open** arrives (folder open, Up, breadcrumb, **Retry** of a failed open). Restarts caused by the filter, **Show hidden** or the sort carry fresh counts but **never** change the layout, and the stored choice is not re-read for them.
- **Grid view — mode switch:** only re-renders the loaded rows (no list request, no new device call); ticks (keyed by path), the lightbox order, pagination state (cursor, sentinel, **Load more**, Retry row) and the filter are untouched. In-flight thumbnail requests are kept where the rebuilt item is the same entry; the rest are re-queued by the usual visibility rules.
- **Grid view — loading state:** the full-panel loading state of an open keeps the layout in effect before the open (the tiles' skeleton in grid, the row skeleton in list); the server's `folder_view` / `stored_view` then apply once page 1 arrives.

## Sorting

- **Keys:** `name` (case-insensitive, ties by exact name), `mtime` (Modified), `size`. `order` `asc` / `desc`.
- **Folders always first**, in every sort and both directions; the key and direction then apply within folders and within files. Folders have no size, so under `size` folders are ordered by name A → Z.
- **Ties** under `mtime` / `size` are broken by name A → Z regardless of direction (case-insensitive, then exact name), so the order is total and stable for keyset paging. Under `name, desc` the whole name order (including the exact-name tie-break) is reversed.
- **Unknown mtime** (`0`) counts as the oldest: last under **Newest first**, first under **Oldest first**; the row shows `—` in Modified.
- **Header clicks:** a click on an inactive column selects it in its natural direction — Name **A → Z**, Modified **newest first**, Size **largest first**; a click on the active column flips its direction. The **Sort** menu sets key and direction directly.
- **Default:** Name, A → Z (first run, after Settings → **Clear preferences**, or a corrupt stored value).
- **Restart:** a sort change restarts at page 1 like the hidden toggle (list dims, no full-panel spinner, scrolled to top), served from the listing cache, keeping the filter, **Show hidden** and every tick; in-flight requests are superseded.
- **Accessibility:** each header button’s accessible name states the column, its current order when active, and what activating it does (e.g. “Modified, sorted newest first. Sort oldest first.”); a visually hidden polite live region announces the new order (“Sorted newest first. Folders stay first.”). Header buttons and the menu are keyboard operable with visible focus.

## Grid view

### Resolution order

The layout of a folder (`list` or `grid`) is the first that applies, evaluated for the folder being opened:

1. **User choice, per folder:** `stored_view` for exactly this `path` (`list` or `grid`). Pressing **List** / **Grid** stores it; **Auto** deletes it. Other folders are unaffected (a choice for `DCIM/Camera` does not apply to `DCIM` or to `DCIM/Camera/Old`).
2. **Folder type:** `folder_view`, from the domain table below.
3. **Auto-detection:** **Grid** when `media_count ≥ 1` **and** `media_count ≥ 60 %` of `entry_count`; otherwise **List** (so an empty folder, or one holding only sub-folders, is a List).

**Folder-type table** (names compared **case-insensitively**, whole path segments):

| Layout | Names |
|---|---|
| **Grid** | `DCIM`, `Pictures`, `Movies`, `Screenshots`, `Camera`, `WhatsApp Images`, `WhatsApp Video`, `Telegram Images`, `Telegram Video` |
| **List** | `Documents`, `Download`, `Android`, `Music`, `Podcasts`, `Recordings` |

The match walks the path **from the folder itself up to the root** and takes the **nearest** segment that is in the table; its layout wins (`DCIM/Camera` → Grid, `Pictures/Instagram` → Grid, `Documents/Photos` → List, `Documents/DCIM` → Grid because `DCIM` is nearer, `DCIM` itself → Grid of folder tiles). The storage root (`""`) and paths with no matching segment give `null`, which falls through to auto-detection.

**Auto-note:** while Auto is selected the control shows `Auto · Grid (photo folder)` or `Auto · List (documents folder)` when the folder type decided, and `Auto · Grid` or `Auto · List` when detection decided.

**Sort, filter and hidden never flip it:** see **Behaviour details**. Counts ignore `query`, so a filter that matches nothing cannot turn a photo folder into a List.

### Tiles

- **Layout:** the same `<ul>` and one `<li>` per entry as in List, laid out as a grid of square tiles with `repeat(auto-fill, minmax(140px, 1fr))`; at ≤ 520 px the minimum is **104 px** (two or three columns). Pagination (sentinel, “Loading more…”, **Load more** footer, inline **Retry** row) and the state panels are unchanged; the footer, “Loading more…” and Retry rows **span the full grid width**.
- **Image/video tile:** the 320 px thumbnail (or video poster with ▶ and duration badge) fills the square (`object-fit: cover`); a **checkbox** overlay at the top left (always visible, large hit area); a **👁** preview button at the top right; the name on **one truncated line** below the square (full name in the tile's `title`). A selected tile has an accent ring.
- **Folder tile:** 📁 in the square and the name; clicking it opens the folder. It has the same checkbox overlay (disabled for `kind: "files"`).
- **Other file tile:** 📄 in the square, no 👁, no preview request.
- **`kind: "folders"`:** file tiles' checkboxes are disabled, and clicking such a tile does nothing. **`mediaOnly`:** non-media tiles are dimmed. Hidden entries (with **Show hidden**) are dimmed.
- **Interactions:** a click on a file tile **toggles its selection** (ignored while its checkbox is disabled); clicks on the checkbox, on 👁 and on a folder tile keep their own meaning (checkbox toggles; 👁 opens the lightbox; a folder tile opens the folder, selecting only via its checkbox). **👁** and **Enter** on a focused photo/video tile open the lightbox; **Space** toggles the selection. The lightbox steps through the **same photo + video order** as in List, and its **Selected** checkbox mirrors the tile's tick.
- **Accessibility:** the grid is a list of tiles, with no `role="grid"` keyboard model. In grid the thumbnail is part of the tile (its click selects), so it is not a separate preview button; the **👁** button keeps `aria-label="Preview <name>"` (`Preview <name> (video, <duration>)` for videos). The tile body is one focus stop whose accessible name is the file name (plus “video, <duration>” where known); the checkbox and 👁 are their own stops with visible focus. The View control is keyboard operable. A visually hidden polite live region (the one that announces sort changes) says **“Grid view”** or **“List view”** when the effective layout changes (not on a re-render that keeps the layout, nor on an open that happens to resolve differently from the previous folder).

## Removal (same change set, after the picker works)

- Remove adbfs: `browse_root` / `peek_browse_root` / `cleanup_orphan_mounts` ADB paths in `adb_repository.py`, `adbfs` in `platform_setup_hints.py`, `docs/legal/THIRD_PARTY_TOOLS.md`, `adbfs` rows in [packaging](../packaging/SPEC.md), the “Mount backends” section and adbfs scenarios in [usb-file-transfer](../usb-file-transfer/SPEC.md), `tests/unit/test_adb_adbfs_browse.py`.
- Remove the native-dialog Browse route/bridge (`usb_transfer.py` host-path picks, `add_usb_transfer_extras_from_host`, `device_relative_paths_from_host_picks`) once nothing else uses them. `host_path_to_device_relative` goes with them; storage-relative paths come straight from the picker.
- Keep: **ifuse** (AFC transfer/listing), `strip_android_user_storage_prefix`, `merge_extra_paths`, extras → `list_extra_file_paths` expansion (now takes picker paths).
- Record the decision in `memory/decisions.md`.

## Acceptance criteria (BDD)

### Scenario: Open from USB file transfer

- **Given** ADB is selected and an authorized phone is connected
- **When** the user activates **Add more**
- **Then** the picker opens at **Phone storage** with breadcrumb `Home / USB file transfer / Pick files or folders`
- **And** the list shows folders before files, no `/sdcard` path anywhere in the UI

### Scenario: Open from USB photo backup

- **Given** USB photo backup Step 1 with ADB or iPhone selected
- **When** the user activates **Add more**
- **Then** the picker opens with breadcrumb `Home / USB photo backup / Pick files or folders` and the media-only note is shown
- **And** Cancel returns to Step 1 with the extras list unchanged

### Scenario: Wi‑Fi has no picker entry

- **Given** USB photo backup Step 1
- **When** Wi‑Fi is the selected connection
- **Then** no **Add more** control is visible

### Scenario: Navigate and multi-select across folders

- **Given** the picker is open
- **When** the user opens `DCIM`, ticks `Camera`, goes up to **Phone storage**, opens `Download`, and ticks `report.pdf`
- **Then** the footer reads “2 items selected” and the button reads **Add 2 items**
- **When** the user activates **Add 2 items**
- **Then** the caller shows `DCIM/Camera` (folder) and `Download/report.pdf` (file) as removable sources

### Scenario: Folder click opens, checkbox selects

- **Given** a folder row
- **When** the user clicks the folder name
- **Then** that folder opens and the selection is unchanged
- **When** the user ticks the row’s checkbox
- **Then** the folder is selected without opening

### Scenario: Select this folder

- **Given** the picker is inside `WhatsApp/Media` (`kind: "folders"`)
- **When** the user activates **Select this folder**
- **Then** `WhatsApp/Media` is added to the selection as a whole folder

### Scenario: Both mode allows files and folders

- **Given** the picker was opened with `kind: "both"` (the **Add more** button)
- **When** a directory with files and sub-folders is listed
- **Then** every row’s checkbox is enabled, **Select this folder** is visible and the breadcrumb ends with `Pick files or folders`
- **When** the user ticks a folder and a file and activates **Add 2 items**
- **Then** both reach the caller (folder as a whole-folder pick)

### Scenario: Folders-only mode disables file checkboxes

- **Given** the picker was opened with `kind: "folders"`
- **When** a directory with files is listed
- **Then** file rows have disabled checkboxes and **Select this folder** is available
- **Given** it was opened with `kind: "files"`
- **When** a directory with sub-folders is listed
- **Then** **Select this folder** is hidden, folder rows can still be opened, and folder checkboxes are disabled

### Scenario: Hidden entries off by default

- **Given** a directory containing `.thumbnails` and `.nomedia`
- **Then** they are not listed
- **When** **Show hidden** is ticked
- **Then** they are listed dimmed

### Scenario: Large folder stays responsive

- **Given** `DCIM/Camera` contains 3,412 files
- **When** the user opens it
- **Then** one directory listing is requested on the device and 100 rows are rendered
- **And** the footer reads “Showing 100 of 3,412 items”
- **And** no sub-folder is listed recursively

### Scenario: Scrolling loads the next page from the cache

- **Given** the first 100 of 3,412 items are shown
- **When** the user scrolls to the bottom of the list
- **Then** a “Loading more…” row appears and the next 100 rows are appended
- **And** no new device call is made (the listing cache is hit) and existing rows are not re-rendered
- **And** the footer reads “Showing 200 of 3,412 items”
- **When** all 3,412 items are loaded
- **Then** the footer is hidden

### Scenario: Load more by keyboard

- **Given** the first page is shown and the footer is visible
- **When** the user focuses **Load more** and activates it with Enter or Space (or the browser has no `IntersectionObserver`)
- **Then** the next 100 rows are appended exactly as when scrolling

### Scenario: Next page fails

- **Given** two pages are loaded and some rows are ticked
- **When** fetching the next page fails
- **Then** the loaded rows and ticks are unchanged and the list ends with “Couldn’t load more items.” and **Retry**
- **When** the user activates **Retry**
- **Then** the same page is requested again (bypassing the listing cache), appended on success, and the Retry row disappears

### Scenario: Folder changes on the phone between pages

- **Given** page 1 of a folder is shown and the listing cache has expired
- **And** a file sorting before the last shown row was added or removed on the phone
- **When** the next page is requested with the cursor from page 1
- **Then** the folder is re-listed once and the page continues after the last shown entry
- **And** no row is duplicated or skipped relative to the entries after that cursor

### Scenario: Invalid cursor

- **Given** a list request whose `cursor` is not a cursor issued by the server
- **When** the route handles it
- **Then** it returns 400 `invalid_cursor` and no `adb` process is started
- **And** when the picker receives it, it restarts from page 1 keeping the ticks

### Scenario: Navigating away drops stale responses

- **Given** a next-page or filter request is in flight
- **When** the user opens another folder
- **Then** the late response is ignored and never appended to the new folder’s list

### Scenario: Filter

- **Given** `DCIM/Camera` contains 3,412 files
- **When** the user types in the filter box and pauses for 200 ms
- **Then** exactly one request is sent, carrying `query`, and the other pages are not loaded
- **And** only matching names show, the list dims until the response arrives, and the footer total is the filtered total
- **When** no name matches
- **Then** the **No match** state appears

### Scenario: Hidden toggle restarts server-side

- **Given** a directory with 150 visible and 10 hidden entries, scrolled to page 2
- **When** the user ticks **Show hidden**
- **Then** a request with `show_hidden: true` restarts at page 1 immediately (no debounce), served from the cache, and the footer total becomes 160

### Scenario: Listing cache

- **Given** the user opened `DCIM/Camera`
- **When** the same folder is opened again within 30 s
- **Then** no device call is made
- **When** it is opened again after 30 s
- **Then** the folder is listed on the device again
- **When** the user activates **Retry** or a request carries `refresh: true`
- **Then** the cache is bypassed and the folder is listed on the device
- **And** a failed listing is never cached, and at most 8 directories are kept (least recently used evicted)

### Scenario: Default sort

- **Given** no sort preference has been stored
- **When** the picker opens at **Phone storage**
- **Then** folders are listed first, then files, each by name A → Z, and the **Name** header shows ▲

### Scenario: Sort by Modified from the header

- **Given** `DCIM/Camera` is open, sorted by name
- **When** the user activates the **Modified** header
- **Then** one request with `sort: "mtime"`, `order: "desc"` restarts at page 1, the newest file is first and **Modified** shows ▼
- **And** no new device call is made (the listing cache is hit) and the ticks and filter are unchanged
- **When** the user activates **Modified** again
- **Then** the order flips to oldest first and **Modified** shows ▲

### Scenario: Folders stay first when sorting by size

- **Given** **Phone storage** with folders and the file `notes.txt`
- **When** the user activates the **Size** header
- **Then** every folder is listed before `notes.txt`, folders ordered by name A → Z, files largest first

### Scenario: Ties fall back to name

- **Given** three files with the same modified time `b.jpg`, `A.jpg`, `c.jpg`
- **When** the folder is sorted newest first (or oldest first)
- **Then** those three appear as `A.jpg`, `b.jpg`, `c.jpg` in both directions

### Scenario: Paging under a non-default sort

- **Given** `DCIM/Camera` (3,412 files, many sharing a modified date) sorted newest first
- **When** the user scrolls until every page is loaded
- **Then** 3,412 rows are shown, none duplicated or skipped, in newest-first order

### Scenario: Cursor from another sort

- **Given** a `next_cursor` issued under `sort: "name"`, `order: "asc"`
- **When** a request sends it with `sort: "mtime"`
- **Then** the route returns 400 `invalid_cursor` and no `adb` process is started
- **And** the picker restarts from page 1 keeping the ticks

### Scenario: Invalid sort values

- **Given** a list request with `sort: "type"`, or `order: "up"`, or `sort` without `order`
- **When** the route handles it
- **Then** it returns 422 and no `adb` process is started

### Scenario: Sort is remembered

- **Given** the user sorted by **Size**, largest first, then closed the picker
- **When** the picker is opened again (from either caller) and the user opens other folders
- **Then** every listing is sorted largest first, and the request that opened the picker carried no `sort` / `order`
- **Given** the stored preference is corrupt, or Settings → **Clear preferences** was used
- **Then** the picker opens sorted Name, A → Z

### Scenario: Narrow window sort menu

- **Given** the picker is ≤ 520 px wide (Modified column hidden)
- **Then** a **Sort** menu is shown in the toolbar with the six options and the current order selected
- **When** the user picks **Newest first**
- **Then** the list restarts sorted newest first, as if the Modified header had been activated

### Scenario: Permission denied

- **Given** the user opens `Android/data`
- **When** the phone refuses the listing
- **Then** the permission-denied state with **Go up** is shown and the selection is untouched

### Scenario: Unauthorized device

- **Given** the phone has not accepted the USB debugging prompt
- **When** the picker lists a directory
- **Then** the unauthorized state with **Retry** is shown

### Scenario: Unplugged mid-browse keeps picks

- **Given** the user has ticked items
- **When** the cable is unplugged and a directory is opened
- **Then** the unplugged state with **Retry** is shown
- **And** the footer still shows the previous count
- **When** the phone is reconnected and Retry is activated
- **Then** the directory lists normally

### Scenario: Empty folder

- **Given** an empty directory
- **When** the user opens it
- **Then** the empty state is shown (mentions hidden files when **Show hidden** is off)

### Scenario: Awkward names

- **Given** files named `résumé final (2).pdf`, `a'b.txt`, `$HOME.txt` and a name containing a newline
- **When** the directory is listed
- **Then** each appears with its exact name, rendered as text, and the Android command receives the directory path as a single quoted argument

### Scenario: Path validation

- **Given** a list request with `path` containing `..` or a NUL byte
- **When** the route handles it
- **Then** the route returns 400 and no `adb` process is started
- **And** an absolute `path` is never read as a host or device-root path: a leading `/` and Android user-storage prefixes are stripped and the rest is treated as relative to phone storage (amended 2026-10-21 in chat to match the code)

### Scenario: Desktop-only

- **Given** a request to `POST /api/device/list` from a non-loopback (LAN) client
- **When** the route handles it
- **Then** it returns 403 `desktop-only` and no `adb` process is started
- **Given** a network passcode is set and a LAN client has no login
- **Then** it receives 401 `passcode-required` first, like other APIs

### Scenario: Preset exist-probe uses one listing

- **Given** ADB is selected and the phone root contains `Download` and `Documents` but not `Music`
- **When** USB file transfer builds its preset checklist
- **Then** exactly one root directory listing is made (it may be served from the listing cache) and only Download and Documents appear

### Scenario: Picked paths are device-relative

- **Given** a pick of `Download/a.pdf`
- **When** the transfer runs
- **Then** the file lands at `Documents/SpaceMaker/Download/a.pdf` (no `sdcard` / `storage/emulated/0` / `storage/self/primary` segment)

### Scenario: Photo backup extras extract media only

- **Given** Step 1 extras contain `WhatsApp/Media` holding photos, videos and a PDF
- **When** extract runs
- **Then** the photos and videos land in `originals/` and the PDF is skipped

### Scenario: Photo backup Start gating

- **Given** USB photo backup with no preset folder ticked and no extras
- **Then** **Start extract** is disabled
- **When** the user adds one extra via the picker
- **Then** **Start extract** is enabled

### Scenario: iPhone through the same picker

- **Given** iPhone (USB) is selected on Linux with a trusted device and the ifuse mount present
- **When** the user opens the picker
- **Then** the root is titled **iPhone**, lists the exposed top-level folders (typically `DCIM`), and one directory is read per navigation

### Scenario: Works on every OS

- **Given** the desktop app on Linux, macOS or Windows (bundled/managed `adb`)
- **When** the user opens the picker
- **Then** it renders and lists the phone without any mount tool, native dialog or extra install

### Scenario: Extras cleared with their session

- **Given** extras were added
- **When** the user changes connection method, leaves to Home, or (photo backup) changes library root
- **Then** the extras list is cleared

### Scenario: adbfs is gone

- **Given** the packaged app and Components screen
- **When** the picker change set is implemented
- **Then** no `adbfs` tool, hint, legal row, or mount code remains

### Scenario: Thumbnail from the embedded EXIF thumbnail

- **Given** a folder contains a camera `IMG_0001.jpg` (4 MB) whose first 64 KB hold an EXIF thumbnail with Orientation 6
- **When** its row becomes visible
- **Then** one head read of 64 KB is made on the device (no full pull) and the row shows an upright 44 px thumbnail
- **And** the thumbnail is shown within ~0.5 s and is stored in the preview cache

### Scenario: Fallback for an image without an embedded thumbnail

- **Given** `IMG-WA0001.jpg` (800 KB, WhatsApp, no EXIF thumbnail)
- **When** its row becomes visible
- **Then** the file is pulled to a temp file, a 320 px JPEG is produced, the temp file is deleted, and the row shows the thumbnail

### Scenario: Too-large image keeps the icon

- **Given** `PANO_0042.jpg` is 40 MB and has no embedded thumbnail
- **When** its row becomes visible
- **Then** the server answers 413 `too_large` without pulling the file, and the row shows the 🖼 glyph with no error text
- **And** the row is still tickable and the 👁 button still opens the lightbox

### Scenario: Preview read fails

- **Given** a thumbnail read times out or the phone is unplugged
- **When** the row's request fails (503)
- **Then** the row shows the 🖼 glyph, the checkbox still works and the footer count is unchanged
- **When** the row leaves and re-enters the viewport
- **Then** the thumbnail is requested again

### Scenario: Only visible rows request thumbnails

- **Given** a folder of 100 loaded rows of which 12 are in the viewport
- **When** the folder opens
- **Then** only those rows request thumbnails, at most 4 are in flight at once, and rows scrolled into view later request theirs

### Scenario: Scrolling away or changing folder cancels pending thumbnails

- **Given** requests are queued or in flight
- **When** the user scrolls them out of view, opens another folder, restarts the list (filter, hidden, sort) or closes the picker
- **Then** the requests are aborted, no late response is applied to another folder's rows, and temp files are removed

### Scenario: Cache hit after reopening the folder

- **Given** the thumbnails of `DCIM/Camera` were generated and the app was restarted
- **When** the folder is opened again
- **Then** the thumbnails are served from the preview cache with no device read for them

### Scenario: Cache key changes with size or mtime

- **Given** `IMG_0001.jpg` has a cached thumbnail
- **When** the listing reports a different `size` or `mtime` for that path
- **Then** the request is a cache miss and the thumbnail is regenerated from the phone
- **And** a client sending a wrong `size` or `mtime` cannot read any other file, only cause a miss

### Scenario: Cache eviction past 200 MB

- **Given** the preview cache holds 200 MB of entries
- **When** a new preview is written
- **Then** the least recently used entries are removed until the cache is ≤ 200 MB, and the new entry is kept
- **And** writes are atomic: a crash mid-write never leaves a partial file that is served

### Scenario: Open the lightbox from the thumbnail and from the 👁 button

- **Given** an image row with a loaded thumbnail
- **When** the user clicks the thumbnail, or activates **👁 Preview** with Enter or Space
- **Then** the lightbox opens on that image showing the blurred thumbnail first, then the large rendition within ~1.5 s
- **And** it shows the name, size, modified date and “n / N”

### Scenario: Step with the arrow keys across previewable rows only

- **Given** the loaded pages hold image rows and non-previewable rows (folders, a PDF)
- **When** the lightbox is open and the user presses → then ←
- **Then** it moves to the next / previous **image or video** row in list order, skipping the others, and “n / N” updates
- **And** → on the last image and ← on the first do nothing (buttons disabled)

### Scenario: Select from the lightbox

- **Given** the lightbox is open on an unticked image
- **When** the user ticks **Selected**, then closes the lightbox
- **Then** the row is ticked and the footer count increased
- **When** the lightbox is reopened and **Selected** is unticked
- **Then** the row is unticked

### Scenario: Lightbox error state

- **Given** the lightbox is open on an image
- **When** the large rendition request fails
- **Then** the lightbox shows “Preview unavailable”, **Selected**, ←/→ and Esc still work

### Scenario: Large file in the lightbox

- **Given** an image over 25 MB with an embedded thumbnail
- **When** the user opens it
- **Then** the upscaled thumbnail is shown with “Full preview unavailable for files over 25 MB” and no full pull is made

### Scenario: Esc returns focus

- **Given** the lightbox was opened from a thumbnail or a 👁 button
- **When** the user presses Esc (or ✕)
- **Then** the lightbox closes and focus returns to that opener
- **And** Tab never leaves the dialog while it is open

### Scenario: Narrow window lightbox

- **Given** the window is ≤ 520 px wide
- **When** the lightbox opens
- **Then** it is full-screen with the ←/→ buttons in a bottom bar, and rows use 36 px thumbnails

### Scenario: Previews yield to a running transfer

- **Given** a USB transfer or extract job is running on the same device
- **When** a row requests its thumbnail
- **Then** the server answers 409 `device_busy` without touching the device, and the row stays a plain icon
- **When** the job has ended and the row becomes visible again
- **Then** the thumbnail is requested and shown

### Scenario: Previews are desktop-only

- **Given** a request to `GET /api/device/thumb` or `/api/device/preview` from a non-loopback (LAN) client
- **When** the route handles it
- **Then** it returns 403 `desktop-only` and no `adb` process is started
- **And** neither route is on `LAN_ALLOWED_ROUTES`

### Scenario: Preview path validation

- **Given** a preview request whose `path` contains `..`, a NUL byte, or an absolute path outside user storage
- **When** the route handles it
- **Then** it returns 400 `invalid_path` and no `adb` process is started

### Scenario: Non-image, non-video or non-file paths

- **Given** a request for a folder, a `.pdf`, a `.cr2`, or a missing file
- **When** the route handles it
- **Then** the server returns 404 `no_preview` and the UI keeps the icon

### Scenario: iPhone previews through the same endpoints

- **Given** iPhone (USB) on Linux with the ifuse mount present and a `DCIM` folder of JPEGs
- **When** the rows become visible and the user opens the lightbox
- **Then** thumbnails and the large rendition come from the same routes, reading the first 64 KB (head) or the whole file from the mount, with the same limits and cache

### Scenario: Previews never touch the library

- **Given** a library is configured
- **When** previews are generated for several photos
- **Then** the cache lives under the app cache directory, and nothing is written into the library or onto the phone

### Scenario: Poster for a camera HEVC clip with moov at the tail

- **Given** `PXL_0001.mp4` is a 416 MB 4K HEVC clip whose `moov` atom is at the end of the file
- **When** its row becomes visible
- **Then** a stream token is minted, ffmpeg reads small head and tail ranges plus the data for the first frame through the stream route (~4.5 MB in total, never the whole file), and the token is revoked
- **And** the row shows the first frame as a 44 px thumbnail with a ▶ glyph and a duration badge, within ~1.5 s
- **And** the JPEG and the duration are stored in the preview cache

### Scenario: Duration badge formats

- **Given** videos of 42.4 s, 12 min 7 s and 1 h 2 min 15 s
- **When** their posters load
- **Then** the badges read `0:42`, `12:07` and `1:02:15`
- **And** each response carried `X-Media-Duration` as decimal seconds

### Scenario: No poster keeps the 🎞 icon and no badge

- **Given** `VID_0004.3gp` has no decodable video stream
- **When** its row becomes visible and the request answers 404 `no_preview`
- **Then** the row shows the 🎞 icon with no ▶ and no duration badge, and no error text
- **And** the checkbox and the 👁 button still work, and nothing is cached

### Scenario: Portrait clip comes out upright

- **Given** a phone clip stored landscape with a −90° rotation tag
- **When** its poster is generated
- **Then** the thumbnail is portrait (e.g. 320×568) and upright, and the large frame is upright too

### Scenario: Unknown duration

- **Given** ffmpeg decodes a frame but prints no usable `Duration:` line
- **When** the poster is served
- **Then** the response has no `X-Media-Duration` header, the row shows the poster with ▶ and no badge, and the lightbox caption omits the duration

### Scenario: Cache hit returns the stored duration

- **Given** the poster of `PXL_0001.mp4` was generated earlier (even before an app restart)
- **When** the row becomes visible again, or the browser revalidates with `If-None-Match`
- **Then** the JPEG comes from the cache with no device call and no ffmpeg run, within 50 ms
- **And** the 200 and the 304 both carry the stored `X-Media-Duration`, so the badge is unchanged

### Scenario: Old cache entries are a miss

- **Given** the cache holds entries written before the format version was bumped
- **When** a poster or photo is requested
- **Then** the old entry is ignored, the item is regenerated, and the new entry is stored with the new version

### Scenario: Videos have no size cap

- **Given** `holiday.mov` is 1.5 GB
- **When** its row becomes visible and the lightbox opens on it
- **Then** both routes answer 200 and neither answers 413 `too_large`
- **And** only ranges were read from the phone

### Scenario: Open the lightbox on a video

- **Given** a video row with a loaded poster
- **When** the user clicks the thumbnail or activates **👁 Preview**
- **Then** the lightbox opens showing the blurred poster with a spinner, then the large frame (≤ 1600 px) within ~2 s
- **And** it shows the caption “Video · 0:42 · 86.0 MB · <date>”, the note “Playback isn’t available in the app yet. Transfer the video to watch it.” and the hint “← → to browse · Esc to close”
- **And** there is no play button and no player

### Scenario: Step across photos and videos

- **Given** the loaded pages hold two photos, a video, a PDF and a photo, in that order
- **When** the lightbox is open on the first photo and the user presses → repeatedly
- **Then** it visits photo, photo, video, photo (skipping the PDF) and the counter reads 1 / 4 … 4 / 4, counting photos and videos together
- **And** → on the last item and ← on the first do nothing

### Scenario: Video lightbox error state

- **Given** the lightbox is open on a video
- **When** the large frame request fails
- **Then** it shows “Video unavailable”, and **Selected**, ←/→ and Esc still work

### Scenario: Stream route honours a single Range

- **Given** a valid token for a 100 MB file
- **When** the client sends `Range: bytes=1000-2999` and then `Range: bytes=50000000-`
- **Then** the first answer is 206 with 2000 bytes and `Content-Range: bytes 1000-2999/100000000`
- **And** the second is 206 truncated to 4 MiB with the matching `Content-Range`

### Scenario: Stream response is capped at 4 MiB

- **Given** a valid token and `Range: bytes=0-33554431`
- **When** the route answers
- **Then** it is 206 with exactly 4 MiB (4 194 304 bytes) and a `Content-Range` that states the bytes actually sent
- **And** `read_range` was called with `length` ≤ 4 MiB

### Scenario: Unsatisfiable range

- **Given** a valid token for a 1 000-byte file
- **When** the client sends `Range: bytes=1000-`
- **Then** the route answers 416 with `Content-Range: bytes */1000` and reads nothing from the phone

### Scenario: Stream request without Range

- **Given** a valid token
- **When** the client sends no `Range` header, or a malformed one (`bytes=a-b`, `bytes=0-1,5-9`)
- **Then** the route answers 400 `range_required` and does not return the first chunk

### Scenario: Unknown or expired token

- **Given** a token that was never minted, was already revoked after its poster finished, or has expired
- **When** it is sent to `GET /api/device/stream`
- **Then** the route answers 404 `unknown_token` and starts no `adb` process

### Scenario: Token is bound to one file

- **Given** a token minted for `DCIM/Camera/PXL_0001.mp4` on device A
- **When** the stream route is called with that token and any other `path`, `device_id` or `method` in the query
- **Then** only the bound file is read and the other values are ignored
- **And** a range beyond the bound `size` is never read

### Scenario: Token lives only for one poster generation

- **Given** a poster generation is running
- **When** it finishes, fails, times out or is aborted
- **Then** its token is revoked and a later request with it answers 404
- **And** no HTTP route returns or accepts the creation of a token

### Scenario: Stream route is desktop-only

- **Given** a request to `GET /api/device/stream` from a non-loopback (LAN) client, even with a valid token
- **When** the route handles it
- **Then** it returns 403 `desktop-only` and no `adb` process is started
- **And** the route is not on `LAN_ALLOWED_ROUTES`, and the [lan-access](../lan-access/SPEC.md) route table lists it as **Desktop**

### Scenario: ffmpeg runs locked down

- **Given** a poster is being generated
- **When** ffmpeg is started
- **Then** its only input is `http://127.0.0.1:<port>/api/device/stream?token=…`, with `-protocol_whitelist http,tcp`, `-frames:v 1` and a 20 s timeout
- **And** a phone file whose bytes try to reference other files or URLs causes no other read

### Scenario: Posters share the four device slots

- **Given** 12 video rows and photo rows are visible
- **When** their requests arrive
- **Then** at most 4 device reads or poster runs are active per device, a poster using 1 slot for its whole ffmpeg run
- **And** the stream route's range reads for ffmpeg do not take additional slots

### Scenario: Posters yield to a transfer before they start

- **Given** a USB transfer or extract job is running on the same device
- **When** a video row requests its poster
- **Then** the server answers 409 `device_busy` without minting a token or touching the device, and the row stays a plain 🎞 icon
- **When** the job has ended and the row becomes visible again
- **Then** the poster is requested and shown

### Scenario: A transfer starts mid-run

- **Given** a poster generation is running
- **When** a transfer or extract job starts on the same device
- **Then** the next stream request answers 409 `device_busy`, ffmpeg fails, and the poster answers 409 `device_busy`
- **And** nothing is cached, the token is revoked, and the row stays a plain icon (not failed)

### Scenario: ffmpeg timeout

- **Given** the phone answers range reads so slowly that ffmpeg exceeds 20 s
- **When** the timeout fires
- **Then** ffmpeg is killed, the token is revoked and the response is 503 `timeout`
- **And** nothing is cached and the row shows the 🎞 icon with no badge
- **When** the row leaves and re-enters the viewport
- **Then** the poster is requested again

### Scenario: Undecodable video

- **Given** a `.mp4` that is truncated or has no video stream
- **When** its poster is requested
- **Then** ffmpeg exits without a frame, the response is 404 `no_preview`, the token is revoked and nothing is cached

### Scenario: Abort kills ffmpeg

- **Given** a poster is being generated
- **When** the user scrolls the row away, opens another folder or closes the picker
- **Then** the request is aborted, ffmpeg is killed, the token is revoked and the slot is released

### Scenario: Unplugged during a poster

- **Given** the phone is unplugged while a poster is being generated
- **When** a range read fails
- **Then** the stream route answers 503 `unplugged`, the poster answers 503 `unplugged`, nothing is cached, and the row shows 🎞 with no badge
- **And** the picker, the ticks and the listing are unaffected

### Scenario: iPhone posters through the same endpoints

- **Given** iPhone (USB) on Linux with the ifuse mount present and a `DCIM` folder of `.MOV` clips
- **When** the rows become visible and the user opens the lightbox
- **Then** posters and large frames come from the same routes, `read_range` seeks and reads from the mount (≤ 4 MiB per response), and the limits, timeout and cache are the same

### Scenario: Posters never touch the library or the phone

- **Given** a library is configured
- **When** posters are generated for several videos
- **Then** JPEGs live only under the app cache directory, temp data is removed, and nothing is written into the library or onto the phone

### Scenario: Camera opens as a grid by folder type

- **Given** nothing is stored for `DCIM/Camera` and the View control is on **Auto**
- **When** the user opens `DCIM/Camera`
- **Then** page 1 reports `folder_view: "grid"`, the folder shows as square tiles with no click, and the note reads “Auto · Grid (photo folder)”
- **And** the Name / Size / Modified header is hidden and the **Sort** menu is shown

### Scenario: Screenshots with two PNGs is a grid

- **Given** `DCIM/Screenshots` holds `a.png` and `b.png` and nothing else
- **When** the user opens it
- **Then** it shows as a grid (folder type, and also `media_count` 2 = 100 %)

### Scenario: Subfolder of Pictures is a grid

- **Given** `Pictures/Instagram` holds three `.txt` files and nothing is stored for it
- **When** the user opens it on Auto
- **Then** it shows as a grid, because the nearest typed ancestor is `Pictures`

### Scenario: Folder type beats detection

- **Given** `Documents/Trip` holds 50 photos and no other file
- **When** the user opens it
- **Then** page 1 reports `folder_view: "list"` and it shows as a list, although `media_count` is 100 %

### Scenario: Nearest typed ancestor wins

- **Given** nothing is stored for `Documents/DCIM`
- **When** the user opens it on Auto
- **Then** it shows as a grid, because `DCIM` is nearer than `Documents`

### Scenario: Untyped folder of only media is a grid by detection

- **Given** `Backup2024` has no typed ancestor and holds 4 photos and nothing else
- **When** the user opens it on Auto
- **Then** `folder_view` is `null`, it shows as a grid, and the note reads “Auto · Grid”

### Scenario: Untyped mixed folder is a list

- **Given** `Misc` holds 3 photos and 7 other files (30 % media)
- **When** the user opens it on Auto
- **Then** it shows as a list and the note reads “Auto · List”

### Scenario: A single photo among few entries

- **Given** `Misc2` holds one photo and one PDF (50 % media) — and, separately, `Misc3` holds one photo and no other entry (100 %); neither has a typed ancestor
- **When** the user opens each on Auto
- **Then** `Misc2` shows as a list and `Misc3` as a grid (the minimum is one photo/video and 60 %)

### Scenario: Folder of only sub-folders is a list

- **Given** an untyped folder holds only sub-folders
- **When** the user opens it on Auto
- **Then** `media_count` is 0 and it shows as a list

### Scenario: Counts ignore the filter and follow the hidden rule

- **Given** an untyped folder holds 10 photos and 10 PDFs, plus 20 hidden photos
- **When** it is listed
- **Then** `entry_count` is 20, `media_count` is 10 (hidden entries are excluded) and it shows as a list
- **When** the user ticks **Show hidden**, then types `.pdf` in the filter
- **Then** the requests carry `entry_count` 40 / `media_count` 30 and then the same counts again (the filter is ignored), and the layout does not change

### Scenario: Filter, sort and hidden do not flip the layout

- **Given** an untyped folder opened as a grid by detection
- **When** the user filters by a name that matches only a PDF, changes the sort, and toggles **Show hidden**
- **Then** it stays a grid after each restart and the note is unchanged
- **And** no layout change is announced

### Scenario: Choice is remembered per folder across reopening and restart

- **Given** `DCIM/Camera` opens as a grid by type
- **When** the user presses **List**
- **Then** the rows show at once without a list request, `PUT /api/device/view` is sent with `{ path: "DCIM/Camera", view: "list" }`, the hint reads **Only this folder** and the live region says “List view”
- **When** the user goes up and opens `DCIM/Camera` again, and again after restarting the app
- **Then** page 1 carries `stored_view: "list"` and it opens as a list with **List** selected and no auto-note

### Scenario: Auto forgets the choice

- **Given** `DCIM/Camera` has a stored `list` choice
- **When** the user presses **Auto**
- **Then** `PUT /api/device/view` is sent with `view: "auto"` (answered 204), the entry is removed, the folder re-resolves to a grid by type with no list request, and the note reads “Auto · Grid (photo folder)”
- **And** deleting an entry that does not exist is also 204

### Scenario: Other folders are unaffected

- **Given** `DCIM/Camera` has a stored `list` choice
- **When** the user opens `DCIM/Screenshots`, `DCIM` and `DCIM/Camera/Old`
- **Then** each is resolved on its own (not from the `Camera` choice) and `stored_view` is `null` for them

### Scenario: The stored map is capped at 500 folders

- **Given** 500 folders have a stored choice
- **When** a choice is stored for a 501st folder
- **Then** the least recently set entry is dropped and the map still holds 500
- **And** setting an existing folder again makes it the most recent, so it is not the next one dropped

### Scenario: Corrupt stored map falls back to Auto

- **Given** the stored `device_picker_views` is not a map, or holds `"DCIM/Camera": "table"`, or a key containing `..`
- **When** the picker opens `DCIM/Camera`
- **Then** the bad value or entry is ignored, valid entries still apply, `stored_view` is `null`, the folder resolves as Auto, and no error is shown

### Scenario: Failed write keeps the session mode

- **Given** the preference file cannot be written
- **When** the user presses **Grid** in `Documents`
- **Then** the folder shows as a grid, no error is shown, and the picker keeps working
- **When** the user leaves and reopens the folder in the same session
- **Then** the client still opens it as a grid
- **When** the app is restarted and the folder is opened
- **Then** it resolves as a List by folder type

### Scenario: Invalid view value

- **Given** a `PUT /api/device/view` with `view: "tiles"`, a missing `view`, or a malformed body
- **When** the route handles it
- **Then** it returns 422 and nothing is stored

### Scenario: View path validation

- **Given** a `PUT /api/device/view` whose `path` contains `..` or a NUL byte
- **When** the route handles it
- **Then** it returns 400 `invalid_path`, nothing is stored and no `adb` process is started
- **And** an absolute `path` (e.g. `/etc/passwd`) is treated as relative to phone storage, like `/api/device/list`: it is stored under the key `etc/passwd` (204), still with no `adb` process

### Scenario: View route is desktop-only

- **Given** a `PUT /api/device/view` from a non-loopback (LAN) client
- **When** the route handles it
- **Then** it returns 403 `desktop-only`, and nothing is stored and no `adb` process is started
- **Given** a network passcode is set and a LAN client has no login
- **Then** it receives 401 `passcode-required` first
- **And** the route is not on `LAN_ALLOWED_ROUTES`, and the [lan-access](../lan-access/SPEC.md) route table lists it as **Desktop**

### Scenario: Later pages omit the grid fields

- **Given** a folder of 250 items is open
- **When** the second page is requested with a `cursor`
- **Then** the response carries no `entry_count`, `media_count`, `folder_view` or `stored_view`, and the layout is unchanged

### Scenario: Switching mode keeps ticks and rows

- **Given** `DCIM/Camera` is open as a grid, two pages are loaded and 5 tiles are ticked
- **When** the user presses **List**, then **Grid**
- **Then** no list request and no device call are made
- **And** the loaded rows are shown in each layout, the 5 ticks and the footer count are unchanged, the scroll stays at the first visible item, and “List view” then “Grid view” are announced

### Scenario: Tile click selects, 👁 opens the lightbox

- **Given** a photo tile in a grid
- **When** the user clicks the tile (not the checkbox or 👁)
- **Then** it becomes selected with the accent ring and the footer count increases; clicking again deselects it
- **When** the user clicks **👁**, or focuses the tile and presses Enter
- **Then** the lightbox opens on that photo and the selection does not change
- **When** the tile has focus and the user presses Space
- **Then** its selection toggles

### Scenario: Lightbox in grid steps the same order

- **Given** a grid holding two photos, a folder tile, a PDF tile and a video
- **When** the lightbox is open on the first photo and the user presses → repeatedly
- **Then** it visits photo, photo, video in list order, skipping the folder and the PDF, counting photos and videos together, and **Selected** mirrors each tile's tick

### Scenario: Folder tile opens the folder

- **Given** a folder tile in a grid
- **When** the user clicks the tile
- **Then** that folder opens and the selection is unchanged
- **When** the user ticks the tile's checkbox instead
- **Then** the folder is selected without opening

### Scenario: Pagination works in grid

- **Given** `DCIM/Camera` (3,412 files) is open as a grid
- **When** the user scrolls to the bottom
- **Then** a “Loading more…” row spanning the full grid width appears and 100 more tiles are appended from the cache with no device call and existing tiles are not re-rendered
- **When** a next-page fetch fails
- **Then** the loaded tiles and ticks stay and a full-width “Couldn’t load more items.” row with **Retry** ends the grid
- **And** the **Load more** footer, activated by keyboard, appends the next 100 tiles

### Scenario: Narrow grid

- **Given** the picker is ≤ 520 px wide with a grid open
- **Then** tiles are at least 104 px (two or three columns), the **Sort** menu is shown, the View control is usable, and there is no horizontal page scroll
- **When** the window is wider than 520 px
- **Then** the **Sort** menu is still shown in grid (in a list it is hidden above 520 px)

### Scenario: Folders-only mode in grid

- **Given** the picker was opened with `kind: "folders"` and a grid is shown
- **When** a folder holds photos
- **Then** the photo tiles' checkboxes are disabled, clicking a photo tile selects nothing, 👁 still opens the lightbox with **Selected** disabled, and folder tiles can be ticked and opened
- **Given** `mediaOnly`
- **Then** non-media tiles are dimmed

### Scenario: Errors look the same in both layouts

- **Given** a grid is selected
- **When** the listing fails (unplugged, unauthorized, permission denied)
- **Then** the same state panel as in a list is shown, the View control stays usable, and ticks are kept

### Scenario: Clear preferences empties the stored views

- **Given** `DCIM/Camera` has a stored `list` choice
- **When** the user uses Settings → **Clear preferences**
- **Then** `device_picker_views` is empty, the client also forgets this session's choices, and the folder opens as a grid by type on the next open

### Scenario: Pixel DNG thumbnail from the embedded preview

- **Given** `DCIM/Camera/PXL_20260305_203512870.RAW-02.ORIGINAL.dng` (15 MB, IFD0 at offset 8, IFD0 Orientation 6, IFD0 = 1280×960 JPEG strip of 330 KB at offset ~4.95 MB with no EXIF)
- **When** its row becomes visible
- **Then** the device reads are: 4 KB at offset 0, then exactly the 330 KB preview range — no full pull
- **And** the row shows an upright (portrait) thumbnail with the **RAW** badge, and the thumbnail is stored in the preview cache

### Scenario: IFD0 at the end of the file

- **Given** a Pixel DNG whose header points to IFD0 about 6 KB before the end of the file
- **When** its thumbnail is requested
- **Then** one extra 4 KB read at the IFD0 offset is made before the preview range read, and the thumbnail is shown
- **And** IFD0's out-of-line BitsPerSample (stored outside that 4 KB) is not read, and IFD0 is still the candidate (no SubIFD read)

### Scenario: iPhone ProRAW DNG

- **Given** `IMG_3809.DNG` (Apple, big-endian `MM`, IFD0 = 3088×2316 JPEG strip of 1.7 MB whose own EXIF says Orientation 6)
- **When** its row becomes visible and then the lightbox opens on it
- **Then** the thumbnail is a 320 px upright JPEG and the lightbox picture is 1600 px on its long edge and upright
- **And** the orientation is applied once (from the preview's EXIF), not twice

### Scenario: Preview picked from a SubIFD

- **Given** a DNG whose IFD0 is a 256×171 uncompressed RGB thumbnail and whose SubIFDs hold a 1024×683 JPEG preview and the CFA raw
- **When** its thumbnail is requested
- **Then** the 1024×683 JPEG is range-read and used, and the raw SubIFD is never read beyond its IFD entries

### Scenario: Largest preview within 1600 px

- **Given** DNG candidates of 320×213, 1024×683 and 4000×3000
- **When** the preview is picked
- **Then** the 1024×683 one is used for both `thumb` and `preview`
- **Given** the only candidate is 4032×3024
- **When** the preview is picked
- **Then** that one is used

### Scenario: Pixel lightbox is not upscaled

- **Given** a Pixel DNG whose only preview is 1280×960
- **When** the lightbox opens
- **Then** the large rendition is 1280×960 (fit-within 1600 never enlarges)

### Scenario: JPEG saved with a .dng name

- **Given** `Pictures/Snapseed/12427.dng` whose bytes start with `FF D8` (a JPEG with an EXIF thumbnail)
- **When** its row becomes visible
- **Then** it is previewed by the photo strategy (EXIF thumbnail from the head read) and shows a thumbnail with the RAW badge

### Scenario: DNG without a usable preview

- **Given** a Lightroom `PXL_20260605_180647686_proxy.dng` whose only image is JPEG XL tiles (Compression 52546)
- **When** its row becomes visible
- **Then** the server answers 404 `no_preview` after the header reads only (no range read of image data), and the row shows the 🖼 glyph with no RAW badge and no error text
- **When** the lightbox opens on it
- **Then** it shows “Preview unavailable — This RAW file has no embedded preview the app can show. You can still select this file.” and stays usable

### Scenario: Not a TIFF or JPEG

- **Given** a `.dng` whose first bytes are neither `FF D8` nor a TIFF header
- **When** its thumbnail is requested
- **Then** the server answers 404 `no_preview` after the first 4 KB read

### Scenario: Large DNG has no size cap

- **Given** an iPhone ProRAW DNG of 52 MB
- **When** its thumbnail is requested
- **Then** it is previewed from the embedded JPEG and never answers 413

### Scenario: Malformed DNG structures are rejected safely

- **Given** DNG bytes with any of: a truncated header, an IFD entry count above 64, an IFD that points back to itself or to an earlier IFD, more than 8 SubIFDs, a preview offset or length beyond the file size, a preview length above 8 MB, or preview bytes not starting with `FF D8`
- **When** the parser runs (both `II` and `MM` byte orders)
- **Then** it returns “no preview” without raising and without reading outside the file, and the route answers 404 `no_preview`

### Scenario: RAW previews share the slots and yield to transfers

- **Given** a USB transfer job is using the device
- **When** a DNG row becomes visible
- **Then** the server answers 409 `device_busy` without any device read, and the row stays a plain icon to be requested again on its next visibility
- **And** while no job runs, at most 4 photo/video/RAW previews read from the device at once

### Scenario: RAW lightbox caption and note

- **Given** the lightbox is open on a folder mixing photos, videos and `.dng` files
- **When** the lightbox shows a `.dng`
- **Then** the caption reads “RAW (DNG) · <size> · <date>”, the note “This is the preview the camera saved inside the RAW file. The RAW data itself isn’t developed here.” is shown, and ←/→ step through photos, videos and RAWs together
- **And** that note is never shown for a photo or a video

### Scenario: DNGs count as media for Auto view

- **Given** an untyped folder holding only `.dng` files
- **When** it opens with no stored choice
- **Then** `media_count` counts the DNGs and Auto detection picks Grid

### Scenario: iPhone ProRAW through AFC

- **Given** iPhone (USB) on Linux with the ifuse mount and `DCIM/100APPLE/IMG_1002.DNG`
- **When** its row becomes visible
- **Then** the header and preview reads are seeks on the mounted file, with the same limits, cache and result as over ADB

## Out of scope

- Browsing the phone’s app-private storage, root-only paths, SD-card/secondary volumes beyond what `/sdcard` exposes (v1: user storage root only).
- In-app video **playback** (Phase B2, see [PLAN-media-preview.md](PLAN-media-preview.md)); RAW formats other than DNG (`cr2`, `cr3`, `nef`, `arw`, `orf`, `rw2`, `raf` keep 📄); developing/demosaicing RAW data, or decoding JPEG XL / lossless-JPEG DNG tiles (DNGs without an embedded JPEG keep the icon); a RAW badge based on file content rather than extension; audio-file previews; motion photos; scrub/hover previews; choosing the poster frame; video previews over LAN; zoom/pan in the lightbox; rotate/edit; previews over Wi‑Fi/LAN.
- Grid view: a tile-size control or pinch zoom; Shift range selection; 2-D arrow-key navigation between tiles (no `role="grid"` model); a grid in the library Gallery (a different feature); a per-**device** view memory (the choice is per folder, shared by every device); a global default view; remembering the choice for a folder's sub-folders; a per-folder sort.
- Search across directories; drag-and-drop.
- Sorting by type/extension, natural/numeric name order (`IMG_2` before `IMG_10`), mixing folders among files, and a per-folder remembered sort.
- Recursive size/count of ticked folders before start.
- Writing to the phone, rename/delete from the picker.
- Wi‑Fi connection method (it already uses the phone’s own browser upload).
- macOS/Windows iPhone (AFC remains Linux-only; see usb-file-transfer).
- Picking the destination folder (PC side).
- Device-side lazy stat (names-first listing, e.g. `ls -1Ap`, then `stat` only the visible page): a possible follow-up for 10k+ folders, deferred until cache + scroll paging is measured on a real phone. toybox `ls` cannot safely represent names containing newlines, so it would need a fallback path.
- Changing the `DeviceRepositoryPort` contract (sorting uses the `mtime` / `size` the listing already returns); gallery pagination and gallery sort controls.
