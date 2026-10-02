# Gallery: Open in Maps

## Metadata

- **Feature:** **Open in Maps ↗** link beside the Location row on the gallery item page
- **Use case:** None (pure presentation logic in the web client; one tiny desktop bridge method)
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — tab "Gallery" → item page (`.gallery-open-maps`)
- **Design decisions approved:** 2026-10-02 (chat)
- **Related:** [gallery](../gallery/SPEC.md) (item metadata panel, `meta.gps`)

## Design decisions

### Success criteria

- An item whose GPS text parses to a valid coordinate shows **Open in Maps ↗** beside the Location text. Clicking it opens Google Maps at that point in the system browser.
- Items with no GPS, or GPS text that cannot be parsed to a valid coordinate, show no link; the raw Location text (if any) is still shown.
- The existing Location text, other metadata rows and the media request are unchanged; the stored `gps` value and the item API are unchanged.
- Works on the desktop app and on LAN phone pages.

### Failure handling

- No new request exists, so nothing can fail server-side.
- Unparseable or out-of-range GPS (latitude outside ±90, longitude outside ±180, missing hemisphere/sign, extra junk) hides the link; the page never links to a guessed or `0,0` point.
- If the desktop bridge is unavailable or the system browser cannot be launched, the click does nothing visible and the app keeps working (no error page, no navigation of the app webview).

### Performance & resource budget

- Pure in-browser string parsing on item open; no new endpoint, subprocess, index field or reindex.
- No network traffic to Google until the user clicks.

### Trust boundary

- The GPS string comes from file EXIF and is **untrusted**. It is parsed with a strict pattern into two finite numbers; the URL is built **only** from those validated numbers (never from raw text) as `https://www.google.com/maps/search/?api=1&query=<lat>,<lon>`.
- The link uses `target="_blank"` and `rel="noopener noreferrer"`.
- In the desktop (pywebview) shell, opening goes through a `js_api` bridge method that **re-validates** the URL server-side: it only opens `https://www.google.com/maps/search/` URLs whose `query` is two in-range decimal numbers, via `webbrowser.open`; anything else is refused. The page's own navigation is never replaced.
- LAN phone clients use the plain link in their own browser; they get no new capability.

## Triggers & routing

- **Entry:** the existing gallery item page `/gallery/item/{relative_path}`, when item metadata with a `gps` value arrives.
- **Data source:** `meta.gps` from `GET /api/gallery/item` (ExifTool `GPSPosition` / `GPSCoordinates` display text, e.g. `52 deg 31' 12.00" N, 13 deg 24' 18.00" E`, or decimal text).

## Visual & UI rules

- Small pill link **Open in Maps ↗** to the right of the Location text, wrapping below it on narrow widths (~320px); styled per `.gallery-open-maps` in the wireframe.
- Shown only when the coordinate parses (see Design decisions).
- Accessible: it is a real `<a>` with visible focus and underline on hover/focus.
- Accepted GPS text forms: degrees-minutes-seconds with `deg`/`°`, `'`, `"` and `N/S/E/W`; decimal degrees with `N/S/E/W`; signed decimal pair `lat, lon`.

## Acceptance criteria (BDD)

### Scenario: Link shown for DMS coordinates

- **Given** an item whose `gps` is `52 deg 31' 12.00" N, 13 deg 24' 18.00" E`
- **When** the item page shows its metadata
- **Then** Location shows that text followed by **Open in Maps ↗**
- **And** the link `href` is `https://www.google.com/maps/search/?api=1&query=52.52,13.405` (decimal, 6 dp max, trailing zeros trimmed)

### Scenario: Link shown for decimal coordinates

- **Given** an item whose `gps` is `52.5200° N, 13.4050° E` or `-33.8688, 151.2093`
- **When** the item page shows its metadata
- **Then** the link points at the matching decimal point, with `S`/`W` (or a minus sign) producing negative values

### Scenario: No link without GPS

- **Given** an item with empty `gps` (e.g. a video without location)
- **When** the item page shows its metadata
- **Then** no Location row link is shown and no **Open in Maps** control exists

### Scenario: No link for unparseable or out-of-range GPS

- **Given** an item whose `gps` is `unknown`, `95 deg 0' 0" N, 10 deg 0' 0" E`, `10, 200`, or text containing extra junk such as `1.0, 2.0"><script>`
- **When** the item page shows its metadata
- **Then** the raw Location text is shown as plain text and **no** link is rendered

### Scenario: Link opens in the system browser on desktop

- **Given** the desktop app with a valid coordinate shown
- **When** the user clicks **Open in Maps ↗**
- **Then** the default browser opens the Google Maps URL and the app webview does not navigate

### Scenario: Desktop bridge refuses other URLs

- **Given** the desktop `open_external_url` bridge method
- **When** it is called with a non-Google-Maps URL, a non-`https` URL, or a Maps URL whose `query` is not two in-range decimals
- **Then** it refuses without opening anything

### Scenario: Stepping between items updates the link

- **Given** the item page is showing a located item
- **When** the user steps to a neighbor with no location (or a different location)
- **Then** the link disappears or points at the new coordinate; it never keeps the previous item's coordinate

## Failure scenarios

| Case | Behavior |
|------|----------|
| GPS text unparseable / out of range | No link; raw text still shown |
| Desktop bridge missing or browser launch fails | Click is a no-op; no navigation, no error page |
| Offline | Browser shows its own offline page; SpaceMaker unaffected |

## Validation rules

- Latitude in [-90, 90], longitude in [-180, 180], both finite; DMS minutes/seconds in [0, 60).
- The Maps URL is only ever assembled from the two validated numbers.
- The desktop bridge allowlists scheme `https`, host `www.google.com`, path `/maps/search/`, and a `query` of exactly `<lat>,<lon>`.

## Testing strategy

| Layer | Coverage |
|-------|----------|
| JS unit (vitest + jsdom, `web/tests/`) | `parseGps` / `mapsUrl`: DMS, decimal, hemisphere/sign, rounding, range limits, junk and injection strings return null |
| JS unit (vitest + jsdom) | Item metadata rendering: link present with correct `href`/`rel`/`target` for located items; absent for empty/unparseable; replaced on re-render |
| Python unit | Desktop `open_external_url` accepts valid Maps URLs (`webbrowser.open` faked) and refuses all others |
| Out of scope | Real browser launch; visual snapshots |

## Out of scope

- Embedding a map, reverse geocoding or showing a place name
- Other map providers or a provider setting
- Altitude, direction or "copy coordinates" actions
- Changing how GPS is probed, stored or indexed
