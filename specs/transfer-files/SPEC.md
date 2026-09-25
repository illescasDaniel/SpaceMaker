# Transfer files (multi-device temporary session)

## Metadata

- **Feature:** Shared Wi‑Fi QR session where the PC and any phones that scan can both upload and download; all session files are deleted when the session ends
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-home` (fifth tile), `#view-transfer-files`; phone [wireframes/phone-transfer.html](../../wireframes/phone-transfer.html). **Wireframe approved** 2026-09-25
- **Spec approved:** 2026-09-25
- **Architecture approved:** _(pending)_
- **Related:** [home-modules](../home-modules/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md)

## Triggers & routing

- Enter from Home → **Transfer files** → `POST /api/module/enter` with `transfer_files` starts a LAN transfer session and issues a session token immediately (QR shown even when the session list is empty).
- Phone page: `GET /transfer?t=…`. Upload: `POST /api/transfer?t=…`. Session list/poll: `GET /api/transfer/session?t=…`. Download: `GET /api/transfer/download?t=…&file_id=…`. QR SVG: `GET /api/transfer/qr.svg` (loopback / desktop).
- Desktop contributes via **Add files** / **Add folder** (pywebview dialogs) → loopback API that copies into the session staging area (not into Documents or the library).
- Breadcrumb or header **Home** (`POST /api/module/home`) **ends** the session: invalidate the token, delete all staged session files, clear the manifest. App quit does the same cleanup.
- Only **one** LAN session at a time (same mutual exclusion as photo upload / receive / send). Entering Transfer files stops any other active LAN session.

## Visual & UI rules

### Desktop (`#view-transfer-files`)

- Breadcrumb **`Home / Transfer files`**.
- Large QR + **ⓘ** (beside the QR, not overlapping) shows the `/transfer` URL and browser fallback.
- Lead: phones on the same Wi‑Fi scan to join; everyone can upload and download until Home.
- Line: files are **temporary**; closing the module deletes everything uploaded in the session.
- **Add files** / **Add folder** always available (no Clear control in v1 — leave via Home).
- **Session files** list: one row per staged item (display name, short origin label, **Download**). Item count status line under the list.
- `--server-only` / browser-only: show hint that Add files/folder need the desktop app; QR and download still work for items already in session.

### Phone (`/transfer`)

- Mix of receive + share UX: **Upload** (Choose files / Choose folder; iOS: single **Choose**, hide folder button) above a **Session files** list with **Download** per row.
- Ephemeral copy: session files are temporary and deleted when the PC closes Transfer files.
- Origin labels: own uploads may show as “from you”; others as “from PC” / “from Phone” (v1 may use a generic remote label).
- Folders appear as a single `.zip` row (button label **Download**, not a separate “Download zip” control).
- Invalid/ended token → ended message (same idea as upload-ended / share expired): scan the QR again on the PC.

## Behavior rules

### Staging & lifetime

- Session files live only in an **ephemeral staging directory** for this transfer session (not `Documents/SpaceMaker/`, not library `originals/`).
- Ending the session (Home, quit, or replacing LAN session by entering another module) **deletes** the staging directory contents. Re-entering Transfer files starts a **new** empty session with a **new** token/QR.

### Uploads (phone or PC)

- **Loose files:** each file becomes one session item (display name = base filename).
- **Folders:** each chosen top-level folder becomes **one** session item: a **`.zip`** named `{folderName}.zip` whose entries preserve the folder tree (empty subfolders omitted). Empty folders (zero files) are rejected with an error; not added to the session.
- Relative multi-file picks that are not a folder zip are stored as individual files (same as receive-files path preservation is **not** required for transfer staging — flat display names; path collisions handled via hash rules below).

### Same name / hash

- Each staged item has a content **hash** (SHA-256 of file bytes; for folder zips, hash of the zip bytes).
- When an upload’s display name **collides** with an existing session item:
  - If the content hash is **identical** → **skip** (idempotent; do not add a second row; do not rewrite staging).
  - If the content hash **differs** → keep both; assign an auto-suffixed display name: `name.ext` → `name (2).ext`, then `name (3).ext`, … (insert before the final extension; names without an extension get `name (2)`).
- Hash is computed when needed for collision checks (and stored on the item for later comparisons).

### Downloads

- Any participant with a valid token can download any session item by `file_id`.
- Desktop **Download** on a row streams that staged file (including `.zip` folder items).
- Phone **Download** same.

## Acceptance criteria (BDD)

### Scenario: Transfer session shows QR on enter

- **Given** the user opened Transfer files from Home
- **When** the module view is shown
- **Then** a scannable QR encodes the `/transfer` URL with a session token
- **And** the session file list is empty
- **And** the status shows zero items

### Scenario: Phone upload appears for everyone

- **Given** an active transfer session
- **When** a phone uploads `notes.txt`
- **Then** `notes.txt` appears in the desktop session list and on other phones’ session lists (after refresh/poll)
- **And** any participant can download it

### Scenario: Desktop can upload into the session

- **Given** an active transfer session
- **When** the user adds a file via **Add files** on the PC
- **Then** that file appears as a session item with origin PC
- **And** phones on `/transfer` can download it

### Scenario: Folder becomes a zip item

- **Given** an active transfer session
- **When** the PC or phone adds a non-empty folder named `vacation`
- **Then** the session lists one item `vacation.zip`
- **And** downloading it yields a zip whose entries match the folder tree (empty subfolders omitted)

### Scenario: Empty folder rejected

- **Given** an active transfer session
- **When** the user adds a folder that contains zero files
- **Then** an error explains the folder is empty
- **And** the session list is unchanged

### Scenario: Same name and same hash skips duplicate

- **Given** the session already contains `report.pdf` with hash H
- **When** another device uploads a file named `report.pdf` with the same content hash H
- **Then** the session still has a single `report.pdf` row
- **And** no auto-suffix is created

### Scenario: Same name and different hash gets a suffix

- **Given** the session already contains `report.pdf` with hash H1
- **When** another device uploads `report.pdf` with a different content hash H2
- **Then** the new item is stored as `report (2).pdf`
- **And** both items remain downloadable

### Scenario: Home deletes all staged files

- **Given** a transfer session with one or more staged files
- **When** the user returns to Home (or quits the app)
- **Then** the transfer token is invalid
- **And** all staged session files are deleted from disk
- **And** re-entering Transfer files shows a new QR and an empty list

### Scenario: Ended token on phone

- **Given** a phone had `/transfer?t=…` open
- **When** the PC ends the session
- **Then** the phone shows that the session has ended
- **And** upload and download are no longer available for that token

### Scenario: Stable QR while items are added

- **Given** Transfer files with an active QR
- **When** the PC or a phone adds more files or folders
- **Then** the transfer URL and QR token stay the same
- **And** participants see the updated list after refresh/poll

## Out of scope

- Replacing or removing Receive files / Send files
- Persisting session files after Home/quit
- Gallery indexing or convert pipeline for transfer items
- “Download all” as one zip of the whole session
- Paired-device history, accounts, or cloud relay
- Unique custom device nicknames beyond simple origin labels (PC vs remote)
- USB/MTP/ADB transfer in this module
