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

- **Layout:** single responsive column (no decorative phone-frame column; narrow viewport is the mobile layout).
- **Toolbar:** title “Gallery”; toggle **Timeline** | **Calendar**.
- **Timeline view:** group by **Year**, then **Month**; responsive thumbnail grid with **`object-fit: cover`** on thumb images.
- **Calendar view:** month navigation (prev/next); weekday header row; days with media highlighted; selecting a day shows that day’s thumbnails below the grid.
- **Mobile:** layout must remain usable at ~320px width.
- **Thumbnails:** served from `{library_root}/.thumbnails/` (cache dir; excluded from convert/extract scans). Lazy-generated on first request via `GET /thumbs/{relative_path}`; browser uses `loading="lazy"`.
- **Video tiles:** poster/thumb image plus a visible **Video** indicator; never use `<img src="…video…">` for the full video file.
- **Performance:** cached thumbs; perceived fast scroll on 1k+ items target.
- **Item page:** route `/gallery/item/{relative_path}` (SPA); back returns to gallery grid. Large preview (`object-fit: contain`, max ~70vh). Metadata block under preview. **Download** (stored file) plus **Download as JPEG** (images) or **Download as MP4** (videos). Export progress in an on-page alert with progress bar; download starts when ready.

## Metadata for grouping

- Primary date: EXIF `DateTimeOriginal` or filesystem mtime fallback.
- Timezone: local machine timezone for display.

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
- **And** metadata appears below the preview
- **And** Download and format-friendly download actions are visible

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

- **Given** an AV1 `.av1.mp4` in `converted/`
- **When** user chooses **Download as MP4**
- **Then** the server encodes H.264 + AAC MP4 (unless already H.264+AAC MP4)
- **And** the UI shows export progress in an alert
- **And** the browser downloads the MP4 when encoding completes

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

## Validation rules

- Index only readable files (optional probe; skip unreadable with log).
- URLs for media must be path-safe (no directory traversal).

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
| Out of scope | Visual snapshot tests until UI stable |

## Out of scope

- Full-screen swipe viewer with pinch-zoom (follow-up feature; item page is not a pinch lightbox)
- Sharing albums publicly outside LAN
- Editing/deleting media from gallery (delete: future spec)
- Face recognition or search
