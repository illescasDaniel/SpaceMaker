# Gallery (processed/ library browser)

## Metadata

- **Feature:** Responsive local web gallery of `processed/` media only
- **Use case:** `GenerateGallery` (index/build) + static/API serve
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — tab “Gallery”
- **Related:** [main-wizard](../main-wizard/SPEC.md) Step 3 (LAN URL + QR); [home-modules](../home-modules/SPEC.md) (Settings → **Reset gallery** wipes the whole library including `processed/`)

## Triggers & routing

- **Entry:** Wizard tab “Gallery”, Step 3 **Open gallery**, or direct URL `/gallery` on LAN. Thumbnail click → `/gallery/item/{relative_path}`.
- **Data source:** Only files under library `processed/` (images avif/jpeg/png/webp/gif as present; videos including `.av1.mp4`).
- **Exclude:** `originals/`, `error/`, `invalid/` never appear in gallery index.

## Visual & UI rules

- **Theme:** system light/dark via shared `theme.css` (`prefers-color-scheme`) on desktop app, mobile gallery shell, and LAN phone pages.
- **Layout:** single responsive column (no decorative phone-frame column; narrow viewport is the mobile layout).
- **Toolbar:** title “Gallery”; toggle **Timeline** | **Calendar**.
- **Timeline view:** group by **Year**, then **Month**; responsive thumbnail grid with **`object-fit: cover`** on thumb images.
- **Calendar view:** month navigation (prev/next); weekday header row; days with media highlighted; selecting a day shows that day’s thumbnails below the grid.
- **Mobile:** layout must remain usable at ~320px width.
- **Thumbnails:** served from `{library_root}/.thumbnails/` (cache dir; excluded from convert/extract scans). Lazy-generated on first request via `GET /thumbs/{relative_path}`; browser uses `loading="lazy"`. Cache paths are a pure function of the source relative path: append `.jpg` to the full relative path (keep the original suffix), e.g. `2025/vacation.avif` → `.thumbnails/2025/vacation.avif.jpg`. This keeps distinct sources from colliding when they share a stem (`vacation.avif` vs `vacation.mp4`). Thumbnail and export cache paths are **not** stored in the gallery index. Generation writes to a temp file beside the cache path and atomically renames it into place, so a concurrent reader never observes a partial thumbnail JPEG. A generation failure returns a non-cached error response (not a long-lived-cached broken image), so the browser retries on the next request instead of caching a dead thumbnail forever; the failure is also recorded in the app log file (see Logging in `docs/ARCHITECTURE.md`) for later diagnosis. The on-disk cache file is also invalidated whenever the thumbnail-generation method changes: a small format-version marker lives alongside `.thumbnails/`, and a mismatch causes the affected cache file to regenerate on next request instead of being reused forever by mtime alone.
- **Thumbnail framing:** the generated thumbnail file itself preserves the source image's exact aspect ratio — fit within a max edge (longest side capped, shorter side scales proportionally; never letterboxed/padded, never center-cropped to a square). Square/cropped framing is a **display-only** CSS concern (`object-fit: cover` in the grid, see above); the cached JPEG bytes are never pre-cropped, so the same file also works as an aspect-correct placeholder on the item page (`object-fit: contain`, see Progressive preview loading below) without a framing mismatch when the full image loads in.
- **Friendly export cache:** on-demand **Download as JPEG** / **Download as MP4** outputs (when a re-encode is needed) live under `{library_root}/.exports/` with the same injective path-mirror rule — append `.jpg` or `.mp4` to the full relative path (e.g. `2025/vacation.avif` → `.exports/2025/vacation.avif.jpg`). Reuse when the cache file exists and is at least as new as the source. Safe to delete anytime; regenerates on the next friendly download. Already-friendly sources (JPEG / H.264+AAC MP4) are served from `processed/` and write nothing under `.exports/`.
- **Video tiles:** poster/thumb image plus a visible **Video** indicator; never use `<img src="…video…">` for the full video file.
- **Performance:** cached thumbs; `/thumbs/` is served `Cache-Control: no-cache` with an `ETag` so the webview/browser always revalidates before use instead of trusting a stale copy for up to a day — a request to the loopback server for an already-generated ~10–50 KB thumbnail is effectively free (the expensive step, `.thumbnails/` disk generation, is already cached separately), so nothing meaningful is lost by not letting the HTTP layer cache it too, and it closes the class of bug where a webview kept serving a pre-fix or pre-reset thumbnail after the source changed (see `memory/decisions.md`). `/media/` (full-size, several MB) keeps a long-lived `Cache-Control` — those bytes are the finished `processed/` file, a relative path is never reused for different content except via **Reset gallery** or a re-import onto the same filename, and re-encoding cost/size make revalidation-per-view worth avoiding; if this bites the same way `/thumbs/` did, apply the same no-cache treatment. Settings → **Clear browser cache** (see [home-modules](../home-modules/SPEC.md)) is the manual escape hatch for the webview's on-disk HTTP cache regardless of which policy is in effect. Image item open starts full media fetch immediately (metadata must not gate it); neighbor thumb/media prefetch after paths are known; a persisted, incrementally-synced index (derived from `processed/` + EXIF/probe metadata, never a source of truth by itself) backs timeline/calendar/day queries and preferably item display metadata so response time does not scale with total library size. Timeline loads via cursor-paginated pages with infinite scroll. Smooth, responsive scrolling at **50,000+ items**, with a bounded mounted-tile working set (not the full library) regardless of scroll distance.
- **Item page:** route `/gallery/item/{relative_path}` (SPA); back returns to gallery grid. Large preview (`object-fit: contain`, `max-height: 55vh` on desktop; phone shell ~50vh). **Previous** / **Next** controls sit **beside** the preview stage (not overlaid on the media), with a clear gutter so they never cover image/video content; media is inset inside the stage frame. Both controls remain visible at the first and last item — the boundary control is **disabled** (muted styling, still opaque — not faded to near-invisible) and does not wrap. Stepping uses **timeline order** (newest-first, same as the grid). Metadata block under preview includes **On disk** (absolute path, full-width wrap). Actions depend on shell:
- **Progressive preview loading:** the preview area reserves its final size up front (never renders at zero/near-zero size). The item's existing thumbnail (`GET /thumbs/{relative_path}` — same one used in the grid) shows immediately as a placeholder using the **same aspect-fit** as the full preview (`object-fit: contain` — letterbox/pillarbox, not cover/crop). A corner status **`• Loading…`** (bottom-left of the media area; no spinner) shows while the full-size preview loads; the full preview then reveals over the thumbnail. This applies on initial open and on every **Previous**/**Next** step.
	- **No extra CSS blur** on the placeholder (no `filter: blur(…)` / scale trick). Natural low-resolution softness from the thumb JPEG is fine.
	- **Smooth scaling:** both the placeholder thumb and the full preview scale with a bilinear-like filter (`image-rendering: auto` / `smooth`) — never nearest-neighbor / pixelated.
	- **Reveal (no blank flash):** wait until the full bitmap is loaded/decoded; fade the full preview in **on top of** the still-visible thumb; only then hide the thumb (do not fade thumb and full out/in together). Prefer a short crossfade duration (~280ms) — smooth but not slow. Respect `prefers-reduced-motion`.
	- **Previous/Next handoff:** keep the outgoing media visible until the incoming thumb covers the stage (overlap + light nudge) — do not blank the stage between items.
	- **Loading chrome:** corner `• Loading…` on a small chip/backdrop; no center spinner.
- **Item open performance:**
	- For **images**, the browser starts `GET /media/{relative_path}` **as soon as the item opens** (path is already known). It must **not** wait for `GET /api/gallery/item` / ExifTool before beginning that fetch. Videos may wait on the item API for `preview_in_browser` before attaching `<video>`.
	- Item metadata (camera, dimensions, GPS, etc.) may appear **after** the full preview has started loading; the meta panel must not gate the media request.
	- Prefer serving display metadata from the derived gallery index when present (populated during index sync) so item open does not re-run ExifTool/ffprobe on every open; fall back to probe when the index lacks those fields.
	- `GET /media/{relative_path}` (inline preview, not forced download) sends long-lived `Cache-Control` so revisit / prev-next / LAN reloads can use the browser cache; `GET /thumbs/{relative_path}` sends `Cache-Control: no-cache` (see Performance above) — the browser still keeps a copy but revalidates via `ETag` before reuse. SPA HTML stays `no-store`. Forced downloads (`?download=1` / `Content-Disposition: attachment`) are unaffected.
	- After neighbors are known, the client **prefetches** `/thumbs/` and `/media/` for the previous and next timeline neighbors so stepping feels snappy.
  - **Desktop app** (`index.html`): **Open** (default app), **Open containing folder**, **Download as JPEG** / **MP4**, **Delete**.
  - **Standalone phone gallery** (`gallery_mobile.html`): **Download**, **Download as JPEG** / **MP4**, **Delete**.
- Export progress in an on-page alert with progress bar.

## Metadata for grouping

- Primary date: EXIF `DateTimeOriginal` or filesystem mtime fallback.
- Timezone: local machine timezone for display.
- Persisted in a local SQLite index (`{library_root}/.index.sqlite`), a derived cache kept in sync with `processed/` via incremental mtime/size diffing on each gallery open — safe to delete at any time; a missing or corrupt index rebuilds automatically.

## LAN & QR

- Server binds `0.0.0.0` on configurable port (default e.g. 8765).
- Step 3 displays `http://{lan_ip}:{port}/gallery`.
- QR encodes the same URL for phone camera scan (SVG or PNG from server; not placeholder text).

## Acceptance criteria (BDD)

### Scenario: Empty processed folder

- **Given** `processed/` is empty
- **When** user opens gallery
- **Then** an empty state message is shown
- **And** no broken thumbnails appear

### Scenario: Timeline groups by year and month

- **Given** media files with dates in 2024 and 2025
- **When** timeline view loads
- **Then** years appear as section headers
- **And** months appear as subheaders with thumbnails beneath

### Scenario: Large library loads incrementally

- **Given** `processed/` contains far more items than fit on screen (tens of thousands)
- **When** timeline view is opened
- **Then** only an initial page of items renders immediately
- **And** scrolling near the bottom loads and appends more pages automatically
- **And** time to first render does not depend on total library size

### Scenario: Mounted gallery tiles stay bounded during a long scroll

- **Given** the user scrolls continuously through a large library
- **When** previously loaded month blocks scroll far out of view
- **Then** their rendered tiles are unmounted and a placeholder holds their scroll space
- **And** scrolling back up re-renders them with no visible layout jump
- **And** the number of mounted tiles stays within a bounded working set regardless of how far the user has scrolled

### Scenario: Incremental index sync after a single change

- **Given** a large library with a populated gallery index
- **When** one file is deleted or added in `processed/`
- **Then** only that file's index entry is updated or removed
- **And** the rest of the library's metadata is not re-probed

### Scenario: External delete drops index and derived caches on next sync

- **Given** a file listed in the gallery index with a thumbnail under `.thumbnails/` and (optionally) a friendly-export cache under `.exports/`
- **And** that file has been removed from `processed/` outside the app (e.g. file browser)
- **When** the gallery next runs its incremental index sync (timeline first page or calendar)
- **Then** that file's index entry is removed
- **And** its `.thumbnails/` cache file is deleted if present
- **And** its `.exports/` cache file(s) for that relative path are deleted if present
- **And** no error is shown to the user

### Scenario: External replace drops stale friendly-export caches on next sync

- **Given** a file in `processed/` with a friendly-export cache under `.exports/`
- **And** that file's mtime or size has changed on disk (replaced outside the app)
- **When** the gallery next runs its incremental index sync
- **Then** that file's index entry is updated
- **And** its `.exports/` cache file(s) for that relative path are deleted if present
- **And** the thumbnail is refreshed on the next thumb request when the source is newer than the cache

### Scenario: Gallery index rebuilds after being missing or corrupt

- **Given** the gallery index file is missing or unreadable
- **When** the gallery is opened
- **Then** the index is rebuilt automatically from `processed/` and EXIF/probe metadata
- **And** no error is shown to the user

### Scenario: Calendar and day views stay fast at scale

- **Given** a library with tens of thousands of items
- **When** the user opens Calendar view or selects a day
- **Then** the month's days-with-media and the selected day's items are computed directly from the index
- **And** response time does not depend on total library size

### Scenario: Calendar highlights days with media

- **Given** at least one file dated on day D
- **When** calendar view is selected
- **Then** day D is visually marked as having media

### Scenario: Gallery ignores non-processed folders

- **Given** files only in `originals/` or `error/`
- **When** gallery index builds
- **Then** those files are not listed

### Scenario: Phone access via LAN URL

- **Given** phone on same network
- **When** user opens LAN gallery URL
- **Then** timeline view renders responsively on narrow viewport

### Scenario: Video thumbnail in grid

- **Given** an `.av1.mp4` in `processed/`
- **When** gallery displays the item
- **Then** a video indicator or poster frame is shown on the tile

### Scenario: Thumbnail generation failure does not stick

- **Given** thumbnail generation fails for a file (e.g. the source is only partially written, or the tool errors)
- **When** `GET /thumbs/{relative_path}` is requested
- **Then** the response is a non-2xx error without long-lived cache headers
- **And** the failure is written to the app log file
- **And** the next request for the same thumbnail retries generation rather than reusing a broken cached response

### Scenario: Open gallery item page

- **Given** a file in `processed/` listed in the gallery
- **When** user opens `/gallery/item/{relative_path}` or clicks its thumbnail
- **Then** a large preview is shown (image or video with controls)
- **And** metadata appears below the preview including the on-disk path
- **And** shell-appropriate actions are visible (desktop vs standalone gallery)

### Scenario: Step through gallery items on item page

- **Given** at least two files in `processed/` in timeline order
- **When** the user opens one item’s detail page
- **Then** **Previous** and **Next** controls are shown **beside** the preview stage (not overlaid on the media)
- **And** media content has inset/gutter so it does not sit under those controls
- **And** **Next** opens the next item in timeline order (older when viewing newest-first)
- **And** **Previous** opens the prior item in timeline order
- **And** the control for the boundary item is disabled but still clearly visible (no wrap)
- **And** stepping to the next/previous item does not flash a blank stage (outgoing media stays until the incoming thumb covers it)
- **And** this works via a per-item neighbor lookup, without requiring the full library's item list to be loaded client-side

### Scenario: Full preview loads progressively from the thumbnail

- **Given** the gallery item page is opening, or the user has just chosen **Previous**/**Next**
- **When** the full-size preview has not finished loading yet
- **Then** the item's existing thumbnail (`GET /thumbs/{relative_path}`) appears immediately in the preview area using **aspect-fit** (`object-fit: contain` — same fit as the eventual full preview)
- **And** a corner status **`• Loading…`** is shown (no spinner)
- **And** the placeholder is **not** given an extra CSS blur filter (low-res softness from the thumb itself is OK)
- **And** the placeholder and full preview use smooth (bilinear-like) image scaling — not nearest-neighbor / pixelated
- **And** the preview area is already at its final size — it does not render at zero or near-zero size while waiting
- **When** the full-size preview has loaded and decoded
- **Then** it fades in on top of the still-visible thumbnail (short smooth transition; no blank flash)
- **And** the thumbnail is hidden only after the full preview is opaque
- **And** the **`• Loading…`** status is removed

### Scenario: Image full preview fetch does not wait on metadata

- **Given** the user opens an **image** gallery item (initial open or Previous/Next)
- **When** the item page begins loading
- **Then** `GET /media/{relative_path}` for that image starts without waiting for `GET /api/gallery/item` to finish
- **And** metadata below the preview may populate when the item API returns (possibly after the media request has already started)

### Scenario: Thumbs and media are cacheable

- **Given** a gallery thumb or inline media URL is requested
- **When** the response is returned (and it is not a forced download)
- **Then** the response includes a long-lived `Cache-Control` header suitable for browser caching

### Scenario: Neighbors are prefetched after item load

- **Given** the user is on a gallery item page with a previous and/or next neighbor in timeline order
- **When** the current item's detail has loaded enough to know those neighbor paths
- **Then** the client prefetches `/thumbs/` and `/media/` for each available neighbor

### Scenario: Delete gallery item from disk

- **Given** the gallery item page for a file in `processed/`
- **When** user confirms **Delete**
- **Then** the file is removed from `processed/` on the host
- **And** its gallery index entry is removed
- **And** its `.thumbnails/` cache file is deleted if present
- **And** its `.exports/` cache file(s) for that relative path are deleted if present
- **And** the user returns to the gallery grid without that item

### Scenario: Download stored file

- **Given** the gallery item page for a processed file
- **When** user chooses **Download**
- **Then** the browser receives the file from `processed/` with `Content-Disposition: attachment`

### Scenario: Export friendly JPEG with progress

- **Given** an AVIF image in `processed/`
- **When** user chooses **Download as JPEG**
- **Then** the server encodes to high-quality JPEG (unless already JPEG)
- **And** the result is cached under `.exports/` at the path-mirrored location for that relative path
- **And** the UI shows export progress in an alert
- **And** the browser downloads the JPEG when encoding completes

### Scenario: Export friendly MP4 with progress

- **Given** an AV1 `.av1.mp4` in `processed/` and a **hardware** H.264 encoder available on the host
- **When** user chooses **Download as MP4**
- **Then** the server encodes H.264 + AAC MP4 with hardware only (unless already H.264+AAC MP4)
- **And** the result is cached under `.exports/` at the path-mirrored location for that relative path
- **And** the UI shows export progress in an alert
- **And** the browser downloads the MP4 when encoding completes

### Scenario: No Download as MP4 without hardware encoder

- **Given** the host has **no** hardware video encoder (no AV1 or H.264 HW)
- **When** the user opens a gallery video item
- **Then** **Download as MP4** is not shown

### Scenario: Video without inline preview

- **Given** a video in `processed/` whose codec is not inline-previewable in the gallery browser (e.g. HEVC)
- **When** the user opens the item page
- **Then** the UI shows metadata and actions but **no** `<video>` preview (message explains codec limitation)

### Scenario: Skip encode when already friendly

- **Given** a JPEG or H.264+AAC MP4 already in `processed/`
- **When** user chooses the matching friendly download
- **Then** no re-encode runs
- **And** download begins immediately

## Failure scenarios

| Case | Behavior |
|------|----------|
| Missing file on disk after index | Remove from index on next refresh; delete matching `.thumbnails/` and `.exports/` caches if present; no 500 page |
| Corrupt media | Show broken placeholder; optional move to invalid via separate admin action (out of scope v1) |
| LAN blocked by firewall | Show note in Step 3; gallery still works locally in pywebview |
| Gallery index file missing or corrupt | Rebuilt automatically from `processed/` + EXIF/probe metadata on next load; no user-facing error |

## Validation rules

- Index only readable files (optional probe; skip unreadable with log).
- URLs for media must be path-safe (no directory traversal).
- Gallery index (`.index.sqlite`) is a derived cache only; deleting it never loses media, it triggers a full rebuild from `processed/` on next load.
- Thumbnail and friendly-export paths are derived from the source relative path (not stored in the index); `.thumbnails/` and `.exports/` are safe to delete anytime.

## Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit | Grouping: given EXIF dates → year/month buckets |
| Unit | Index excludes paths outside `processed/` |
| Unit | Calendar mark algorithm for day sets |
| Integration | HTTP GET `/gallery` returns 200 with fixture tree in `tmp_path` |
| Integration | GET `/api/gallery/calendar` returns month + days-with-media; GET `/thumbs/…` returns JPEG after first request |
| Integration | GET `/gallery/item/…` SPA 200; GET `/api/gallery/item`; export POST + download |
| Unit | Path safety; friendly-format skip; injective export/thumbnail cache naming |
| Unit | SPA path helper / snapshot includes `visualize` step state (see main-wizard spec) |
| Unit | Index sync diff: added/changed/removed files computed from mtime/size comparison against the index |
| Unit | Sync removes orphan `.thumbnails/` and `.exports/` for removed paths; drops stale exports for changed paths |
| Unit | In-app delete removes processed file, index row, thumbnail, and export caches |
| Unit | Keyset pagination cursor stability, including ties on identical `captured_at` |
| Unit | Calendar/day queries return correct results directly from the index at month/day boundaries |
| Unit | Neighbor (prev/next) lookup at both boundaries returns no wrap |
| Integration | `GET /api/gallery/timeline` paginates via cursor/limit; a second page continues after the first with no duplicates or gaps |
| Integration | `GET /api/gallery/item/neighbor` returns the correct adjacent item, and null at boundaries |
| Out of scope | Visual snapshot tests until UI stable |

## Out of scope

- Full-screen swipe viewer with pinch-zoom (follow-up feature; item page is not a pinch lightbox)
- Sharing albums publicly outside LAN
- Storing thumbnail or export cache paths (or existence flags) in `.index.sqlite`
- Face recognition or search
- Editing media from gallery (crop/rotate/etc.)
- Library wipe / reset UI (owned by [home-modules](../home-modules/SPEC.md) Settings → **Reset gallery**)
