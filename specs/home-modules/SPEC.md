# Home modules hub

## Metadata

- **Feature:** Home hub with module tiles; header **Home | Gallery**
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-home`, module screens. **Wireframe approved** 2026-09-23 (hub, breadcrumbs, QR + ⓘ); **updated** 2026-09-25 (fifth tile **Transfer files** — wireframe approved).
- **Spec approved:** 2026-09-23; **updated** 2026-09-25 (fifth module — see [transfer-files](../transfer-files/SPEC.md))
- **Architecture approved:** 2026-09-23
- **Related:** [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md)

## Triggers & routing

- **Default on launch:** `#view-home` (no Wi‑Fi session until a module is opened).
- **Header:** **Home** returns to the hub via `POST /api/module/home` (stops that module’s LAN session). **Gallery** unchanged.
- **Module enter:** `POST /api/module/enter` with `{ "module": "photo_backup" | "usb_photo_backup" | "receive_files" | "send_files" | "transfer_files" }`.
- Only **one** LAN session at a time (photo upload, receive-files, send-files, or transfer-files).

## Visual & UI rules

- **Home:** 2-column grid of square tiles with inline icons and titles: Photo backup, USB photo backup, Receive files, Send files, **Transfer files** (fifth tile; third row).
- Each module screen shows breadcrumbs **`Home / {module title}`** — **Home** is tappable (same as **Back to Home** / `POST /api/module/home`); the module name is larger and bold. No separate back button.
- **Theme:** all modules and Gallery use **system light/dark** (`theme.css` + `prefers-color-scheme`); layout differs per module, not palette.

## Acceptance criteria (BDD)

### Scenario: App opens on Home hub

- **Given** SpaceMaker starts with a valid library root
- **When** the desktop client loads
- **Then** the Home hub is shown
- **And** no Wi‑Fi extract/receive/share/transfer session is active

### Scenario: Home breadcrumb stops LAN session

- **Given** the user is in Receive files with an active QR session
- **When** they tap **Home** in the breadcrumb (or header **Home**)
- **Then** the receive session ends
- **And** the Home hub is shown

### Scenario: Transfer files tile opens the module

- **Given** the Home hub is shown
- **When** the user taps **Transfer files**
- **Then** `#view-transfer-files` is shown
- **And** a transfer LAN session is active (see [transfer-files](../transfer-files/SPEC.md))

## Out of scope

- Persisting last-open module across restarts
