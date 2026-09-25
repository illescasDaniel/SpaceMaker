# Gallery (converted/ library browser)

## Metadata

- **Feature:** Responsive local web gallery of `converted/` media only
- **Use case:** `GenerateGallery` (index/build) + static/API serve
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — tab “Gallery”
- **Related:** [main-wizard](../main-wizard/SPEC.md) Step 3 (LAN URL + QR)

## Triggers & routing

- **Entry:** Wizard tab “Gallery”, Step 3 **Open gallery**, or direct URL `/gallery` on LAN. Thumbnail click → `/gallery/item/{relative_path}`.
- **Data source:** Only files under library `converted/` (images avif/jpeg/png/webp/gif as present; videos including `.av1.mp4`).
- **Exclude:** `originals/`, `error/`, `invalid/` never appear in gallery index.

## Visual & UI rules

- **Theme:** system light/dark via shared `theme.css` (`prefers-color-scheme`) on desktop app, mobile gallery shell, and LAN phone pages.
- **Layout:** single responsive column (no decorative phone-frame column; narrow viewport is the mobile layout).
- **Toolbar:** title “Gallery”; toggle **Timeline** | **Calendar**.
- **Timeline view:** group by **Year**, then **Month**; responsive thumbnail grid with **`object-fit: cover`** on thumb images.
- **Calendar view:** month navigation (prev/next); weekday header row; days with media highlighted; selecting a day shows that day’s thumbnails below the grid.
- **Mobile:** layout must remain usable at ~320px width.
- **Thumbnails:** served from `{library_root}/.thumbnails/` (cache dir; excluded from convert/extract scans). Lazy-generated on first request via `GET /thumbs/{relative_path}`; browser uses `loading="lazy"`.
- **Video tiles:** poster/thumb image plus a visible **Video** indicator; never use `<img src="…video…">` for the full video file.
- **Performance:** cached thumbs; a persisted, incrementally-synced index (derived from `converted/` + EXIF/probe metadata, never a source of truth by itself) backs timeline/calendar/day queries so response time does not scale with total library size. Timeline loads via cursor-paginated pages with infinite scroll. Smooth, responsive scrolling at **50,000+ items**, with a bounded mounted-tile working set (not the full library) regardless of scroll distance.
- **Item page:** route `/gallery/item/{relative_path}` (SPA); back returns to gallery grid. Large preview (`object-fit: contain`, `max-height: 55vh` on desktop; phone shell ~50vh). **Previous** / **Next** overlay buttons on the preview move to the adjacent item in **timeline order** (newest-first, same as the grid); disabled at the first/last item. Metadata block under preview includes **On disk** (absolute path, full-width wrap). Actions depend on shell:
- **Progressive preview loading:** the preview area reserves its final size up front (never renders at zero/near-zero size). The item's existing thumbnail (`GET /thumbs/{relative_path}` — same one used in the grid) fills it immediately as a placeholder, with a loading indicator over it, while the full-size preview loads in the background; the full preview then replaces the thumbnail. This applies on initial open and on every **Previous**/**Next** step.
  - **Desktop app** (`index.html`): **Open** (default app), **Open containing folder**, **Download as JPEG** / **MP4**, **Delete**.
  - **Standalone phone gallery** (`gallery_mobile.html`): **Download**, **Download as JPEG** / **MP4**, **Delete**.
- Export progress in an on-page alert with progress bar.

## Metadata for grouping

- Primary date: EXIF `DateTimeOriginal` or filesystem mtime fallback.
- Timezone: local machine timezone for display.
- Persisted in a local SQLite index (`{library_root}/.index.sqlite`), a derived cache kept in sync with `converted/` via incremental mtime/size diffing on each gallery open — safe to delete at any time; a missing or corrupt index rebuilds automatically.

## LAN & QR

- Server binds `0.0.0.0` on configurable port (default e.g. 8765).
- Step 3 displays `http://{lan_ip}:{port}/gallery`.
- QR encodes the same URL for phone camera scan (SVG or PNG from server; not placeholder text).

## Acceptance criteria (BDD)

### Scenario: Empty converted folder

- **Given** `converted/` is empty
- **When** user opens gallery
- **Then** an empty state message is shown
- **And** no broken thumbnails appear

### Scenario: Timeline groups by year and month

- **Given** media files with dates in 2024 and 2025
- **When** timeline view loads
- **Then** years appear as section headers
- **And** months appear as subheaders with thumbnails beneath

### Scenario: Large library loads incrementally

- **Given** `converted/` contains far more items than fit on screen (tens of thousands)
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
- **When** one file is deleted or added in `converted/`
- **Then** only that file's index entry is updated or removed
- **And** the rest of the library's metadata is not re-probed

### Scenario: Gallery index rebuilds after being missing or corrupt

- **Given** the gallery index file is missing or unreadable
- **When** the gallery is opened
- **Then** the index is rebuilt automatically from `converted/` and EXIF/probe metadata
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

### Scenario: Gallery ignores non-converted folders

- **Given** files only in `originals/` or `error/`
- **When** gallery index builds
- **Then** those files are not listed

### Scenario: Phone access via LAN URL

- **Given** phone on same network
- **When** user opens LAN gallery URL
- **Then** timeline view renders responsively on narrow viewport

### Scenario: Video thumbnail in grid

- **Given** an `.av1.mp4` in `converted/`
- **When** gallery displays the item
- **Then** a video indicator or poster frame is shown on the tile

### Scenario: Open gallery item page

- **Given** a file in `converted/` listed in the gallery
- **When** user opens `/gallery/item/{relative_path}` or clicks its thumbnail
- **Then** a large preview is shown (image or video with controls)
- **And** metadata appears below the preview including the on-disk path
- **And** shell-appropriate actions are visible (desktop vs standalone gallery)

### Scenario: Step through gallery items on item page

- **Given** at least two files in `converted/` in timeline order
- **When** the user opens one item’s detail page
- **Then** **Previous** and **Next** controls are shown on the preview
- **And** **Next** opens the next item in timeline order (older when viewing newest-first)
- **And** **Previous** opens the prior item in timeline order
- **And** the control for the boundary item is disabled (no wrap)
- **And** this works via a per-item neighbor lookup, without requiring the full library's item list to be loaded client-side

### Scenario: Full preview loads progressively from the thumbnail

- **Given** the gallery item page is opening, or the user has just chosen **Previous**/**Next**
- **When** the full-size preview has not finished loading yet
- **Then** the item's existing thumbnail (`GET /thumbs/{relative_path}`) fills the preview area immediately, with a loading indicator over it
- **And** the preview area is already at its final size — it does not render at zero or near-zero size while waiting
- **And** once the full-size preview loads, it replaces the thumbnail and the loading indicator is removed

### Scenario: Delete gallery item from disk

- **Given** the gallery item page for a file in `converted/`
- **When** user confirms **Delete**
- **Then** the file is removed from `converted/` on the host
- **And** the user returns to the gallery grid without that item

### Scenario: Download stored file

- **Given** the gallery item page for a converted file
- **When** user chooses **Download**
- **Then** the browser receives the file from `converted/` with `Content-Disposition: attachment`

### Scenario: Export friendly JPEG with progress

- **Given** an AVIF image in `converted/`
- **When** user chooses **Download as JPEG**
- **Then** the server encodes to high-quality JPEG (unless already JPEG)
- **And** the UI shows export progress in an alert
- **And** the browser downloads the JPEG when encoding completes

### Scenario: Export friendly MP4 with progress

- **Given** an AV1 `.av1.mp4` in `converted/` and a **hardware** H.264 encoder available on the host
- **When** user chooses **Download as MP4**
- **Then** the server encodes H.264 + AAC MP4 with hardware only (unless already H.264+AAC MP4)
- **And** the UI shows export progress in an alert
- **And** the browser downloads the MP4 when encoding completes

### Scenario: No Download as MP4 without hardware encoder

- **Given** the host has **no** hardware video encoder (no AV1 or H.264 HW)
- **When** the user opens a gallery video item
- **Then** **Download as MP4** is not shown

### Scenario: Video without inline preview

- **Given** a video in `converted/` whose codec is not inline-previewable in the gallery browser (e.g. HEVC)
- **When** the user opens the item page
- **Then** the UI shows metadata and actions but **no** `<video>` preview (message explains codec limitation)

### Scenario: Skip encode when already friendly

- **Given** a JPEG or H.264+AAC MP4 already in `converted/`
- **When** user chooses the matching friendly download
- **Then** no re-encode runs
- **And** download begins immediately

## Failure scenarios

| Case | Behavior |
|------|----------|
| Missing file on disk after index | Remove from index on next refresh; no 500 page |
| Corrupt media | Show broken placeholder; optional move to invalid via separate admin action (out of scope v1) |
| LAN blocked by firewall | Show note in Step 3; gallery still works locally in pywebview |
| Gallery index file missing or corrupt | Rebuilt automatically from `converted/` + EXIF/probe metadata on next load; no user-facing error |

## Validation rules

- Index only readable files (optional probe; skip unreadable with log).
- URLs for media must be path-safe (no directory traversal).
- Gallery index (`.index.sqlite`) is a derived cache only; deleting it never loses media, it triggers a full rebuild from `converted/` on next load.

## Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit | Grouping: given EXIF dates → year/month buckets |
| Unit | Index excludes paths outside `converted/` |
| Unit | Calendar mark algorithm for day sets |
| Integration | HTTP GET `/gallery` returns 200 with fixture tree in `tmp_path` |
| Integration | GET `/api/gallery/calendar` returns month + days-with-media; GET `/thumbs/…` returns JPEG after first request |
| Integration | GET `/gallery/item/…` SPA 200; GET `/api/gallery/item`; export POST + download |
| Unit | Path safety; friendly-format skip; export cache naming |
| Unit | SPA path helper / snapshot includes `visualize` step state (see main-wizard spec) |
| Unit | Index sync diff: added/changed/removed files computed from mtime/size comparison against the index |
| Unit | Keyset pagination cursor stability, including ties on identical `captured_at` |
| Unit | Calendar/day queries return correct results directly from the index at month/day boundaries |
| Unit | Neighbor (prev/next) lookup at both boundaries returns no wrap |
| Integration | `GET /api/gallery/timeline` paginates via cursor/limit; a second page continues after the first with no duplicates or gaps |
| Integration | `GET /api/gallery/item/neighbor` returns the correct adjacent item, and null at boundaries |
| Out of scope | Visual snapshot tests until UI stable |

## Out of scope

- Full-screen swipe viewer with pinch-zoom (follow-up feature; item page is not a pinch lightbox)
- Sharing albums publicly outside LAN
- Editing/deleting media from gallery (delete: future spec)
- Face recognition or search
