# Home modules hub

## Metadata

- **Feature:** Home hub with module tiles; header **Home | Gallery | Settings**
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-home`, module screens, `#view-settings`. **Wireframe approved** 2026-09-23 (hub, breadcrumbs, QR + ⓘ); **updated** 2026-09-25 (fifth tile **Transfer files**); **USB file transfer tile approved** 2026-09-26; **updated** 2026-09-27 (3-column **4:3** tiles, floating footer); **updated** 2026-09-27 (centered hub + default window **960×720** — wireframe approved with transfer download UX); **updated** 2026-09-27 (sticky header; **Home | Gallery | Settings**; settings menu; default window **1152×864**; no floating footer — wireframe approved).
- **Spec approved:** 2026-09-23; **updated** 2026-09-25 (fifth module — see [transfer-files](../transfer-files/SPEC.md)); **USB file transfer addition** with [usb-file-transfer](../usb-file-transfer/SPEC.md); **re-approved** 2026-09-27 (layout + footer chrome); **re-approved** 2026-09-27 (centered hub / window size); **re-approved** 2026-09-27 (sticky header, Settings tab, settings menu, 1152×864)
- **Architecture approved:** 2026-09-23; **re-approved** 2026-09-27 (no new ports — inbound static + `window_geometry` for Home polish; transfer save is [transfer-files](../transfer-files/SPEC.md)); clear-preferences / reset-library ports approved with photo-backup Settings work
- **Related:** [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [usb-file-transfer](../usb-file-transfer/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md), [legal](../legal/SPEC.md), [gallery](../gallery/SPEC.md), [packaging](../packaging/SPEC.md)

## Triggers & routing

- **Default on launch:** `#view-home` (no Wi‑Fi session until a module is opened).
- **Header tabs:** **Home** | **Gallery** | **Settings**.
  - **Home** returns to the hub via `POST /api/module/home` (stops that module’s LAN session or USB transfer job).
  - **Gallery** unchanged (gallery browser).
  - **Settings** shows `#view-settings` (does not stop a LAN session unless product later requires it).
- **Module enter:** `POST /api/module/enter` with `{ "module": "photo_backup" | "usb_photo_backup" | "usb_file_transfer" | "receive_files" | "send_files" | "transfer_files" }`.
- Only **one** LAN session at a time (photo upload, receive-files, send-files, or transfer-files). USB file transfer does not start a LAN session.

## Visual & UI rules

- **Sticky header:** `.top-bar` stays fixed at the top of the window; only the content area below (`.app-main`) scrolls. Not a floating/overlay header — layout is a column with a non-scrolling chrome strip.
- **Home hub content:** module tiles only — **no** lead/subtitle under the header (e.g. no “Choose what you want to do…”). Wireframe-only notes (`.wf-note`, `.wf-demo`, top banner) are **not** product UI.
- **Home layout:** `#view-home` centers the module grid both horizontally and vertically in the window.
- **Default desktop window:** **1152×864** (4:3, +20% from prior 960×720) via desktop window geometry; minimum size unchanged (**800×600**) unless product later requires it.
- **Home grid:** **3-column** grid of tiles. Tile order: Photo backup, USB photo backup, **USB file transfer**, Receive files, Send files, **Transfer files**.
- **Tile shape:** each tile is **4:3** (`aspect-ratio: 4 / 3`), compact width (~8.75rem columns in the wireframe). Icons stay **3rem**; titles stay **~0.92rem** bold — shrinking the tile does **not** shrink icon or title type.
- **No floating footer:** Settings and About & Legal are **not** footer links. Branding footer chrome is removed.
- **Settings screen** (`#view-settings`): friendly list of four actions, in this order:
  1. **Clear preferences** — inline confirm, then wipe all disk-backed user preferences (e.g. Compress media) so defaults apply again.
  2. **Reset gallery** — inline confirm, then delete the entire library under the session library root: `originals/`, `processed/`, `error/`, `invalid/`, `.thumbnails/`, `.exports/`, and the gallery index (`.index.sqlite`). Recreate empty library folders afterward.
  3. **Downloaded components** — opens nested `#view-settings-tools` (managed tools folder, delete/retry — same behavior as [packaging](../packaging/SPEC.md) / prior Settings tools body). **← Settings** returns to the menu.
  4. **About & Legal** (last) — opens `#view-legal` ([legal](../legal/SPEC.md)). **← Settings** returns to the menu.
- Each module screen shows breadcrumbs **`Home / {module title}`** — **Home** is tappable (same as **Back to Home** / `POST /api/module/home`); the module name is larger and bold. No separate back button.
- **Theme:** all modules and Gallery use **system light/dark** (`theme.css` + `prefers-color-scheme`); layout differs per module, not palette.

## Acceptance criteria (BDD)

### Scenario: App opens on Home hub

- **Given** SpaceMaker starts with a valid library root
- **When** the desktop client loads
- **Then** the Home hub is shown
- **And** the hub shows the six module tiles in a 3-column grid with 4:3 tiles
- **And** the module grid is centered in the window
- **And** the hub does not show a lead/subtitle under the header
- **And** no Wi‑Fi extract/receive/share/transfer session is active

### Scenario: Default window is 1152×864

- **Given** the user launches the desktop app (not `--server-only`)
- **When** the main window opens
- **Then** the default size is 1152×864 (4:3)

### Scenario: Sticky header; content scrolls below

- **Given** any main view with content taller than the window
- **When** the user scrolls
- **Then** the header (logo + Home | Gallery | Settings) stays at the top
- **And** only the content below the header scrolls

### Scenario: Header tabs include Settings

- **Given** the Home hub is shown
- **When** the user looks at the header tabs
- **Then** the tabs are **Home**, **Gallery**, and **Settings**
- **And** no floating footer with Settings or About & Legal is shown

### Scenario: Settings menu order and actions

- **Given** the user opens the **Settings** tab
- **When** `#view-settings` is shown
- **Then** the actions appear in order: Clear preferences, Reset gallery, Downloaded components, About & Legal

### Scenario: Clear preferences requires confirm

- **Given** the Settings menu is shown and a Compress media preference is stored
- **When** the user taps **Clear preferences**
- **Then** an inline confirmation is shown
- **When** they confirm
- **Then** all disk-backed user preferences are removed
- **And** Compress media returns to its default resolution (on when tools available)

### Scenario: Reset gallery requires confirm and wipes library

- **Given** the Settings menu is shown and the library has files in `originals/` and/or `processed/` (and optionally `error/`, `invalid/`, caches)
- **When** the user taps **Reset gallery**
- **Then** an inline confirmation is shown
- **When** they confirm
- **Then** library buckets `originals/`, `processed/`, `error/`, `invalid/` are emptied (or removed and recreated)
- **And** `.thumbnails/`, `.exports/`, and `.index.sqlite` under the library root are removed
- **And** the Gallery shows empty

### Scenario: Downloaded components nested screen

- **Given** the Settings menu is shown
- **When** the user taps **Downloaded components**
- **Then** `#view-settings-tools` shows the managed tools folder and delete/retry controls
- **When** they tap **← Settings**
- **Then** `#view-settings` is shown again

### Scenario: About and Legal from Settings

- **Given** the Settings menu is shown
- **When** the user taps **About & Legal**
- **Then** `#view-legal` is shown
- **When** they tap **← Settings**
- **Then** `#view-settings` is shown again

### Scenario: Home breadcrumb stops LAN session

- **Given** the user is in Receive files with an active QR session
- **When** they tap **Home** in the breadcrumb (or header **Home**)
- **Then** the receive session ends
- **And** the Home hub is shown

### Scenario: USB file transfer tile opens module

- **Given** the user is on the Home hub
- **When** they activate **USB file transfer**
- **Then** the USB file transfer view is shown
- **And** no Wi‑Fi receive/share/transfer session is started

### Scenario: Transfer files tile opens the module

- **Given** the Home hub is shown
- **When** the user taps **Transfer files**
- **Then** `#view-transfer-files` is shown
- **And** a transfer LAN session is active (see [transfer-files](../transfer-files/SPEC.md))

## Out of scope

- Persisting last-open module across restarts
- Changing module set, order, or names (beyond layout/chrome and the USB file transfer addition above) without a new wireframe + spec gate
- Cancelling in-flight extract/convert jobs as part of Reset gallery (v1 may require idle library or best-effort wipe)
