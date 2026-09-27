# Home modules hub

## Metadata

- **Feature:** Home hub with module tiles; header **Home | Gallery**
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-home`, module screens. **Wireframe approved** 2026-09-23 (hub, breadcrumbs, QR + ⓘ); **updated** 2026-09-25 (fifth tile **Transfer files**); **updated** 2026-09-27 (3-column **4:3** tiles, floating footer); **updated** 2026-09-27 (centered hub + default window **960×720** — wireframe approved with transfer download UX).
- **Spec approved:** 2026-09-23; **updated** 2026-09-25 (fifth module — see [transfer-files](../transfer-files/SPEC.md)); **re-approved** 2026-09-27 (layout + footer chrome); **re-approved** 2026-09-27 (centered hub / window size)
- **Architecture approved:** 2026-09-23; **re-approved** 2026-09-27 (no new ports — inbound static + `window_geometry` for Home polish; transfer save is [transfer-files](../transfer-files/SPEC.md))
- **Related:** [easy-mode](../easy-mode/SPEC.md), [main-wizard](../main-wizard/SPEC.md), [receive-files](../receive-files/SPEC.md), [send-files](../send-files/SPEC.md), [transfer-files](../transfer-files/SPEC.md), [legal](../legal/SPEC.md)

## Triggers & routing

- **Default on launch:** `#view-home` (no Wi‑Fi session until a module is opened).
- **Header:** **Home** returns to the hub via `POST /api/module/home` (stops that module’s LAN session). **Gallery** unchanged.
- **Module enter:** `POST /api/module/enter` with `{ "module": "photo_backup" | "usb_photo_backup" | "receive_files" | "send_files" | "transfer_files" }`.
- Only **one** LAN session at a time (photo upload, receive-files, send-files, or transfer-files).

## Visual & UI rules

- **Home hub content:** module tiles only — **no** lead/subtitle under the header (e.g. no “Choose what you want to do…”). Wireframe-only notes (`.wf-note`, `.wf-demo`, top banner) are **not** product UI.
- **Home layout:** `#view-home` centers the module grid both horizontally and vertically in the window.
- **Default desktop window:** **960×720** (4:3) via desktop window geometry; minimum size unchanged unless product later requires it.
- **Home grid:** **3-column** grid of tiles. Tile order: Photo backup, USB photo backup, Receive files, Send files, **Transfer files** (fifth tile starts the second row).
- **Tile shape:** each tile is **4:3** (`aspect-ratio: 4 / 3`), compact width (~8.75rem columns in the wireframe). Icons stay **3rem**; titles stay **~0.92rem** bold — shrinking the tile does **not** shrink icon or title type.
- **Global footer:** on every main view, a **floating** footer (fixed near the bottom edge, centered, elevated surface — not a full-width border strip). Links: **Settings** and **About & Legal** (same destinations as [legal](../legal/SPEC.md) / [main-wizard](../main-wizard/SPEC.md)). Main content has bottom clearance so it is not covered by the footer.
- Each module screen shows breadcrumbs **`Home / {module title}`** — **Home** is tappable (same as **Back to Home** / `POST /api/module/home`); the module name is larger and bold. No separate back button.
- **Theme:** all modules and Gallery use **system light/dark** (`theme.css` + `prefers-color-scheme`); layout differs per module, not palette.

## Acceptance criteria (BDD)

### Scenario: App opens on Home hub

- **Given** SpaceMaker starts with a valid library root
- **When** the desktop client loads
- **Then** the Home hub is shown
- **And** the hub shows the five module tiles in a 3-column grid with 4:3 tiles
- **And** the module grid is centered in the window
- **And** the hub does not show a lead/subtitle under the header
- **And** no Wi‑Fi extract/receive/share/transfer session is active

### Scenario: Default window is compact 4:3

- **Given** the user launches the desktop app (not `--server-only`)
- **When** the main window opens
- **Then** the default size is 960×720 (4:3)

### Scenario: Floating footer stays available on Home

- **Given** the Home hub is shown
- **When** the user looks at the bottom of the window
- **Then** a floating footer with **Settings** and **About & Legal** is visible
- **And** it does not use a full-width edge-to-edge strip layout

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
- Changing module set, order, or names (beyond layout/chrome above)
