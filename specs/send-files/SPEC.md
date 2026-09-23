# Send files (PC → phone)

## Metadata

- **Feature:** Pick files/folders on desktop; phone downloads via QR `/share` page
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-send-files`; phone [wireframes/phone-share.html](../../wireframes/phone-share.html). **Wireframe approved** 2026-09-23 (desktop hub + phone share page).
- **Spec approved:** 2026-09-23
- **Architecture approved:** 2026-09-23
- **Related:** [home-modules](../home-modules/SPEC.md)

## Triggers & routing

- Enter from Home → **Send files**. Selection is **session-only** (cleared on Home or quit).
- Desktop: **Add files** / **Add folder** via pywebview dialogs → `POST /api/share/selection` with absolute paths.
- When the manifest is non-empty, show QR to `GET /share?t=…`. Downloads: `GET /api/share/download?t=…&file_id=…`.
- Breadcrumb or header **Home** stops the share session and clears selection.

## Visual & UI rules

- Breadcrumb **`Home / Send files`**. List selected paths on desktop. QR hidden until at least one file is shared. **ⓘ** beside the QR (not overlapping) shows the share page URL and browser fallback. No duplicate example URL line in the body.
- Phone page lists files with per-file **Download** links.
- `--server-only` / browser-only: show hint to use the desktop app to pick files.

## Acceptance criteria (BDD)

### Scenario: Share QR after selection

- **Given** the user added at least one file in Send files
- **When** the server builds the manifest
- **Then** a QR is shown for the share page
- **And** the phone can download each listed file

### Scenario: Selection cleared on Home

- **Given** Send files with a non-empty selection
- **When** the user returns to Home
- **Then** the share session ends
- **And** the selection is empty on re-entry

## Out of scope

- Zip “download all”
- Persisting selection across restarts
