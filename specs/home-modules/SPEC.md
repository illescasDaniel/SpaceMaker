# Home modules hub

## Metadata

- **Feature:** Home hub with module tiles; header **Home | Gallery**
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-home`, module screens. **Wireframe approved** 2026-09-23 (hub, breadcrumbs, QR + ⓘ); **USB file transfer tile approved** 2026-09-26.
- **Spec approved:** 2026-09-23 (four modules); **USB file transfer addition** pending approval with [usb-file-transfer](../usb-file-transfer/SPEC.md)
- **Architecture approved:** 2026-09-23
- **Related:** [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [usb-file-transfer](../usb-file-transfer/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md)

## Triggers & routing

- **Default on launch:** `#view-home` (no Wi‑Fi session until a module is opened).
- **Header:** **Home** returns to the hub via `POST /api/module/home` (stops that module’s LAN session or USB transfer job). **Gallery** unchanged.
- **Module enter:** `POST /api/module/enter` with `{ "module": "photo_backup" | "usb_photo_backup" | "usb_file_transfer" | "receive_files" | "send_files" }`.
- Only **one** LAN session at a time (photo upload, receive-files, or send-files). USB file transfer does not start a LAN session.

## Visual & UI rules

- **Home:** 2-column grid of square tiles with inline icons and titles: Photo backup, USB photo backup, **USB file transfer**, Receive files, Send files (five tiles; last row may have a single tile).
- Each module screen shows breadcrumbs **`Home / {module title}`** — **Home** is tappable (same as **Back to Home** / `POST /api/module/home`); the module name is larger and bold. No separate back button.
- **Theme:** all modules and Gallery use **system light/dark** (`theme.css` + `prefers-color-scheme`); layout differs per module, not palette.

## Acceptance criteria (BDD)

### Scenario: App opens on Home hub

- **Given** SpaceMaker starts with a valid library root
- **When** the desktop client loads
- **Then** the Home hub is shown
- **And** no Wi‑Fi extract/receive/share session is active

### Scenario: Home breadcrumb stops LAN session

- **Given** the user is in Receive files with an active QR session
- **When** they tap **Home** in the breadcrumb (or header **Home**)
- **Then** the receive session ends
- **And** the Home hub is shown

### Scenario: USB file transfer tile opens module

- **Given** the user is on the Home hub
- **When** they activate **USB file transfer**
- **Then** the USB file transfer view is shown
- **And** no Wi‑Fi receive/share session is started

## Out of scope

- Persisting last-open module across restarts
- More than the five modules listed above (without a new wireframe + spec gate)
