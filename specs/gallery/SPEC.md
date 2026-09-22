# Gallery (converted/ library browser)

## Metadata

- **Feature:** Responsive local web gallery of `converted/` media only
- **Use case:** `GenerateGallery` (index/build) + static/API serve
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — tab “Gallery”
- **Related:** [main-wizard](../main-wizard/SPEC.md) Step 3 (LAN URL + QR)

## Triggers & routing

- **Entry:** Wizard tab “Gallery”, Step 3 **Open gallery**, or direct URL `/gallery` on LAN.
- **Data source:** Only files under library `converted/` (images avif/jpeg/png/webp/gif as present; videos including `.av1.mp4`).
- **Exclude:** `originals/`, `error/`, `invalid/` never appear in gallery index.

## Visual & UI rules

- **Toolbar:** title “Gallery”; toggle **Timeline** | **Calendar** (wireframe).
- **Timeline view:** group by **Year**, then **Month**; responsive thumbnail grid (CSS object-fit cover in production).
- **Calendar view:** month grid; days with media highlighted (count or dot); selecting day filters grid (v1: show month subset).
- **Mobile:** layout must remain usable at ~320px width (wireframe phone frame).
- **Performance:** lazy-load thumbnails; generate or cache thumbs on first index (implementation detail — spec requires perceived fast scroll on 1k+ items target).

## Metadata for grouping

- Primary date: EXIF `DateTimeOriginal` or filesystem mtime fallback.
- Timezone: local machine timezone for display.

## LAN & QR

- Server binds `0.0.0.0` on configurable port (default e.g. 8765).
- Step 3 displays `http://{lan_ip}:{port}/gallery`.
- QR encodes the same URL for phone camera scan.

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
| Out of scope | Visual snapshot tests until UI stable |

## Out of scope

- Full-screen swipe viewer with pinch-zoom (follow-up feature)
- Sharing albums publicly outside LAN
- Editing/deleting media from gallery (delete: future spec)
- Face recognition or search
