# Download all

## Metadata

- **Feature:** A **Download all** button on every page that lists a few downloadable files (phone Send files `/share`, phone Transfer files `/transfer`, desktop Transfer files screen) that delivers the whole list as one `.zip`. The Gallery is not touched.
- **Wireframe:** [phone-share.html](../../wireframes/phone-share.html), [phone-transfer.html](../../wireframes/phone-transfer.html), [app.html](../../wireframes/app.html) (`#view-transfer-files`). **Wireframe approved** 2026-10-29 (chat)
- **System design:** [design/download-all/DESIGN.md](../../design/download-all/DESIGN.md). **Design approved** 2026-10-29 (chat)
- **Design decisions approved:** 2026-10-29 (chat)
- **Spec approved:** 2026-10-29 (chat)
- **Related:** [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md), [lan-access](../lan-access/SPEC.md), [network-passcode](../network-passcode/SPEC.md)

## Design decisions

### Success criteria

- With 2 or more rows, one tap gives the user every item in a single zip; nothing is silently left out unless the file no longer exists.
- No file is overwritten or renamed on disk: only entry names inside the zip are de-duplicated (`name (2).ext`).
- Zero residue: the phone temp zip is deleted after the response; a failed build leaves no temp file.
- Existing per-row Download buttons and folder zips behave exactly as before.

### Failure handling

- Token invalid or session ended (F1) → `403`; phone shows the existing "ended" panel, desktop shows an alert.
- Nothing downloadable (F2) → `404 nothing to download`; alert "Nothing to download".
- A file vanished while zipping (F3) → that item is skipped, the rest are zipped; if none remain it is F2.
- Zip cannot be written, e.g. disk full (F4) → `500`, temp file removed, alert "Could not build the zip"; the session and lists are untouched, the user can retry.
- No partial state to resume: each tap builds a new zip.

### Performance & resource budget

- Entries are stored uncompressed (`ZIP_STORED`): low CPU on the PC; items are mostly already-compressed media/PDF.
- Streamed from disk file by file, never held in memory; temp disk use is about the total size of the items. No size cap beyond free temp disk (same as today's folder zips).
- No polling and no new background jobs; the button is shown or hidden from the already-polled manifest.

### Trust boundary

- Untrusted: the `t` token and any query string from LAN clients. The token is validated by the existing `share_token_valid` / `transfer_token_valid` before anything is read; the endpoints take no file ids or paths from the client, so the client cannot choose what goes into the zip.
- Trusted: the server-side manifest (share paths chosen on the PC; transfer items already staged under the session root).
- Entry names inside the zip come from display names and are sanitized (no `..`, no absolute paths, no drive letters, `/` separators).
- Desktop `POST /api/transfer/save-all` is loopback only, like `/api/transfer/save`; it writes only to the Documents/SpaceMaker receive root.
- Respects the LAN passcode like the other `/api/share/*` and `/api/transfer/*` routes (the lan-access route allow-list gains the two new GET paths, not the POST).

### Compatibility & rollout

- Purely additive: no existing endpoint, stored data or client changes; older open phone pages simply lack the button.
- No flag. Rollback = remove the button and the three routes.

## Triggers & routing

- **Entry (phone Send):** `GET /api/share/download-all?t=…`, a plain link on the list page.
- **Entry (phone Transfer):** `GET /api/transfer/download-all?t=…`, a plain link on the session page.
- **Entry (desktop Transfer):** loopback `POST /api/transfer/save-all` from the **Download all** button.
- **Exit:** phone: the browser's own download; desktop: the existing `Saved to {display path}` tip. Failure: existing ended panel (phone) or alert (desktop). The user stays on the page.

## Visual & UI rules

- Button copy: phone **Download all (.zip)**, desktop **Download all**. Placed above the list (phone) / in the "Session files" header row (desktop), as in the approved wireframes.
- Visible only when the list has **2 or more** rows; recomputed on every poll (so it appears when the second item arrives and disappears if the session ends).
- Phone Send/Transfer: full-width accent button, same press animation as the other buttons; it is a link (`<a download>`), so no JS needed to download.
- Desktop: secondary button; while the zip builds the button is disabled; success reuses the existing "Saved to …" tip.
- Wireframe-only "Review only" notes do not ship.

## Interfaces & contracts

- `GET /api/share/download-all?t=` → `200 application/zip`, `Content-Disposition: attachment; filename="SpaceMaker-share.zip"`. Contents: every manifest row; file rows by name, folder rows as `<folder>/…` with relative paths.
- `GET /api/transfer/download-all?t=` → same, filename `SpaceMaker-transfer.zip`. Contents: every staged item by display name; folder items stay as their `.zip`.
- `POST /api/transfer/save-all` (loopback) → `200 {saved_path, saved_name, saved_path_display}` with the zip placed in the Documents receive root using the existing no-overwrite naming.
- Errors: `403 session ended`, `404 nothing to download`, `500 could not build zip`.
- Duplicate entry names inside the zip get ` (2)`, ` (3)`, …. GET is repeatable; each desktop POST creates a new file.

## Data & migration

None. No stored data changes.

## Acceptance criteria

### Scenario: phone Send files downloads everything as one zip

**Given** a share of `report.pdf` and the folder `vacation/` **When** the phone taps **Download all (.zip)** **Then** it receives `SpaceMaker-share.zip` containing `report.pdf` and `vacation/…` with relative paths, and the server temp zip is deleted.

### Scenario: phone Transfer files includes items from every device

**Given** a transfer session with `notes.txt` from the PC and `report.pdf` from a phone **When** a phone taps **Download all (.zip)** **Then** it receives `SpaceMaker-transfer.zip` with both files.

### Scenario: desktop Download all saves one zip to Documents

**Given** a transfer session with 3 items **When** the desktop user clicks **Download all** **Then** `SpaceMaker-transfer.zip` is saved in `~/Documents/SpaceMaker/` and the UI shows `Saved to …`.

### Scenario: desktop save never overwrites an existing zip

**Given** `SpaceMaker-transfer.zip` already exists in Documents/SpaceMaker **When** the user clicks **Download all** again **Then** the new file is `SpaceMaker-transfer (2).zip` and the first is untouched.

### Scenario: button hidden with fewer than two rows

**Given** a list with 0 or 1 rows **When** the page renders **Then** no **Download all** button is shown; it appears once a second row arrives.

### Scenario: same names are kept apart inside the zip

**Given** two transfer items both named `report.pdf` **When** Download all runs **Then** the zip holds `report.pdf` and `report (2).pdf`, and both sources are unchanged on disk.

### Scenario: session ended (F1)

**Given** the session was ended or the token is wrong **When** `download-all` is requested **Then** the response is `403`, no file is read, and the phone page shows its ended panel.

### Scenario: nothing to download (F2)

**Given** a valid session whose items were all removed **When** `download-all` is requested **Then** the response is `404 nothing to download`.

### Scenario: a file vanished while zipping (F3)

**Given** a share of 3 files and one is deleted on the PC before zipping reaches it **When** Download all runs **Then** the zip contains the other 2 files and the request succeeds.

### Scenario: zip cannot be written (F4)

**Given** the temp disk is full **When** Download all runs **Then** the response is `500`, no temp zip remains, the user sees "Could not build the zip", and the session is unchanged.

### Scenario: client cannot choose paths

**Given** a request with extra `file_id` or `path` query parameters **When** it reaches `download-all` **Then** they are ignored and only the server-side manifest is zipped.

### Scenario: hostile names cannot escape the zip

**Given** an item whose name contains `../` or an absolute path **When** it is zipped **Then** the entry name is sanitized to a plain relative name inside the archive.

### Scenario: desktop save endpoint is loopback only

**Given** a LAN client that is not loopback **When** it calls `POST /api/transfer/save-all` **Then** it is rejected like `/api/transfer/save`.

### Scenario: LAN passcode still applies

**Given** a network passcode is set and the client has not unlocked **When** it requests `download-all` **Then** it is refused like the other share/transfer routes.

## Out of scope

- Gallery downloads (existing batch zip), USB pages, Receive files.
- Selecting a subset of rows, a Save-as dialog on desktop, compression options, a size cap, progress bars.
- Changing per-row Download or folder-zip behavior.
