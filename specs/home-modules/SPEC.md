# Home modules hub

## Metadata

- **Feature:** Home hub with four module tiles; header **Home | Gallery**
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-home`, module screens. **Wireframe approved** 2026-09-23 (hub, breadcrumbs, QR + ⓘ).
- **Spec approved:** 2026-09-23
- **Architecture approved:** 2026-09-23
- **Related:** [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md)

## Triggers & routing

- **Default on launch:** `#view-home` (no Wi‑Fi session until a module is opened).
- **Header:** **Home** returns to the hub via `POST /api/module/home` (stops that module’s LAN session). **Gallery** unchanged.
- **Module enter:** `POST /api/module/enter` with `{ "module": "photo_backup" | "usb_photo_backup" | "receive_files" | "send_files" }`.
- Only **one** LAN session at a time (photo upload, receive-files, or send-files).

## Visual & UI rules

- **Home:** 2×2 grid of square tiles with inline icons and titles: Photo backup, USB photo backup, Receive files, Send files.
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

## Out of scope

- Persisting last-open module across restarts
- More than four modules
