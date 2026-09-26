# Receive files (phone → PC)

## Metadata

- **Feature:** Wi‑Fi QR receive of arbitrary files into Documents
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-receive-files`; phone [wireframes/phone-receive.html](../../wireframes/phone-receive.html). **Wireframe approved** 2026-09-23 (desktop hub + phone receive page).
- **Spec approved:** 2026-09-23
- **Architecture approved:** 2026-09-23
- **Related:** [home-modules](../home-modules/SPEC.md)

## Triggers & routing

- Enter from Home → **Receive files** → `POST /api/module/enter` with `receive_files` starts a LAN receive session.
- Phone page: `GET /receive?t=…` (not `/upload`). Upload API: `POST /api/receive?t=…`.
- Breadcrumb or header **Home** stops the session (`POST /api/module/home`).

## Visual & UI rules

- Desktop: breadcrumb **`Home / Receive files`**. Same layout as Photo backup (large QR, transfer progress). **ⓘ** beside the QR (not overlapping) shows the receive page URL + browser fallback. No convert block. Line: *Files are saved under `~/Documents/SpaceMaker/`* only (no extra ⓘ hint in that line). **Open documents folder** is shown only when at least one file exists under the receive root. That action opens `{documents}/SpaceMaker/` in the OS file manager when that folder exists; if the user removed it (or open fails), open the user’s **Documents** directory instead (do not recreate SpaceMaker on open).
- Destination: `documents_directory()/SpaceMaker/` (create if missing). Preserve relative paths from the phone.

## Acceptance criteria (BDD)

### Scenario: Receive session shows QR

- **Given** the user opened Receive files from Home
- **When** the module view is shown
- **Then** a scannable QR encodes the `/receive` URL
- **And** transfer count starts at zero

### Scenario: Phone upload lands in Documents

- **Given** an active receive session
- **When** the phone uploads `reports/2024/summary.pdf`
- **Then** the file exists under `{documents}/SpaceMaker/reports/2024/summary.pdf`
- **And** the desktop transfer count increases

## Out of scope

- Gallery indexing or convert pipeline
- USB/MTP/ADB/AFC receive (see [usb-file-transfer](../usb-file-transfer/SPEC.md))
