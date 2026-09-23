# Send files (PC → phone)

## Metadata

- **Feature:** Pick files/folders on desktop; phone downloads via QR `/share` page
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-send-files`; phone [wireframes/phone-share.html](../../wireframes/phone-share.html). **Wireframe approved** 2026-09-23 (desktop hub + phone share page); **updated** 2026-09-23 (folder zip rows on phone page).
- **Spec approved:** 2026-09-23; **updated** 2026-09-23 (folder zip downloads).
- **Architecture approved:** 2026-09-23
- **Related:** [home-modules](../home-modules/SPEC.md)

## Triggers & routing

- Enter from Home → **Send files**. Selection is **session-only** (cleared on Home or quit).
- Desktop: **Add files** / **Add folder** via pywebview dialogs → `POST /api/share/selection` with absolute paths.
- When the manifest is non-empty, show QR to `GET /share?t=…`.
- Downloads: `GET /api/share/download?t=…&file_id=…` — single files as-is; each **top-level folder** from **Add folder** as a **`.zip`** (contents preserve relative paths inside the archive).
- **Share token:** issued when the first shareable item is added; **reused** when the user adds more files/folders or removes items (until **Clear**, **Home**, or quit). The QR/URL must not change on each add.
- Breadcrumb or header **Home** stops the share session and clears selection.

## Visual & UI rules

- Breadcrumb **`Home / Send files`**. List selected paths on desktop. QR hidden until at least one file is shared. **ⓘ** beside the QR (not overlapping) shows the share page URL and browser fallback. No duplicate example URL line in the body.
- Phone page: one row per **top-level** selected path — loose files with **Download**; folders labeled **(folder)** with **Download zip** (saves `{folderName}.zip`).
- `--server-only` / browser-only: show hint to use the desktop app to pick files.

## Acceptance criteria (BDD)

### Scenario: Empty folder rejected

- **Given** Send files with no selection (or an existing selection)
- **When** the user adds a folder that contains zero files (empty subfolders alone do not count)
- **Then** an error dialog explains the folder is empty
- **And** that folder is not added to the desktop path list
- **And** no share QR is shown until at least one file is shareable

### Scenario: Share QR after selection

- **Given** the user added at least one file or folder in Send files
- **When** the server builds the manifest
- **Then** a QR is shown for the share page
- **And** the phone can download each listed item

### Scenario: Folder downloads as zip on phone

- **Given** the user added a top-level folder that contains one or more files (any nesting)
- **When** the phone opens the share page
- **Then** the folder appears as one row (not one row per file inside it)
- **And** **Download zip** delivers a `.zip` whose entries match the folder tree (empty subfolders omitted)

### Scenario: Loose files download individually

- **Given** the user added one or more files via **Add files**
- **When** the phone opens the share page
- **Then** each file has its own row and **Download** link (not zipped together)

### Scenario: Stable QR while adding items

- **Given** Send files with an active share QR
- **When** the user adds another file or folder (or removes one without clearing all)
- **Then** the share URL and QR token stay the same
- **And** the phone share page lists the updated manifest (after refresh/poll)

### Scenario: Selection cleared on Home

- **Given** Send files with a non-empty selection
- **When** the user returns to Home
- **Then** the share session ends
- **And** the selection is empty on re-entry

## Out of scope

- One zip for the entire mixed selection (“download all”)
- Persisting selection across restarts
