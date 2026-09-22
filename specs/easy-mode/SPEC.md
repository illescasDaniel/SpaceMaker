# Easy mode (default UI)

## Metadata

- **Feature:** Minimal default UI — Wi‑Fi upload QR, auto-receive, convert-as-received, **View gallery** when ready; phone gallery help on Gallery tab
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-easy`, Easy | Advanced toggle; phone upload [wireframes/phone-upload.html](../../wireframes/phone-upload.html)
- **UX approved:** 2026-09-22 (chat: wireframe approved)
- **Related:** [main-wizard](../main-wizard/SPEC.md), [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [gallery](../gallery/SPEC.md)

## Triggers & routing

- **Default on launch:** **Easy** mode (`ui_mode=easy`). **Advanced** shows the existing three-step wizard.
- **Session:** `ui_mode` is session-only (relaunch → Easy). User may switch Easy ↔ Advanced anytime; **does not** stop active Wi‑Fi receive or convert drain.
- **Header tabs:** **Main** (Easy or Advanced home) and **Gallery** remain. Gallery chrome uses the **active mode theme** (light in Easy, dark in Advanced).
- **Easy bootstrap:** When the client loads Easy and extract is idle, the server starts **Wi‑Fi receive** automatically (library root from session defaults; no Start extract button).

## Visual & UI rules

### Easy (light, minimalist)

- Off-white background, white surfaces, dark text, generous spacing.
- Vertical stack (centered, max ~28rem):
  1. **Large upload QR** (active Wi‑Fi session)
  2. Short instruction: scan with phone on same Wi‑Fi
  3. **Transfer** progress (files received this session; total unknown → count + optional indeterminate bar while receiving)
  4. **Convert** progress (same WebSocket convert job as Advanced). When idle with files already in `converted/`, status reads e.g. **1 file converted, waiting for more** (pluralized).
  5. **View gallery** button — **only when** `converted/` count **> 0**; switches to the **Gallery** tab (same as Main → Gallery).
  6. **Gallery tab (desktop):** circular **phone help** control (bottom-right); tap opens a popup with gallery LAN URL, QR, and *Please don't open this while uploading content.* (same information as the former Easy gallery block). Hidden on phone gallery shell.
- No library picker, connection toggle, or extract/convert buttons on Easy.
- Phone **upload** page (`/upload`): light, minimal; footer hint varies for **iPhone vs Android** (UA detection). **iPhone:** single **Choose** button (no folder picker). **Android:** **Choose files** + **Choose folder**.
- Phone **gallery** (`/gallery` on device browser): dedicated mobile shell (no Easy/Advanced or Main/Gallery chrome); theme follows **system** light/dark via `shell-gallery.css`. Server serves `gallery_mobile.html` for **private LAN** hosts; loopback/desktop app keeps full `index.html`.
- Phone **upload** page shows **files sent** count from `/api/upload/session` (`files_sent`).

### Advanced (dark)

- Unchanged three-step wizard ([main-wizard](../main-wizard/SPEC.md)).

## Convert while receiving (Easy only)

- After each completed Wi‑Fi upload (saved or size-skipped), if convert is **idle** and `originals/` is non-empty, start convert **without** stopping extract.
- When a convert batch finishes, if `originals/` still has files and Easy concurrent policy applies, start another batch.
- **Advanced** **Start convert** still **stops extract first** then converts ([convert-media](../convert-media/SPEC.md)).

## Acceptance criteria (BDD)

### Scenario: Easy launches with upload QR

- **Given** SpaceMaker starts with default library root
- **When** the client opens Easy mode
- **Then** Wi‑Fi extract is **running** without clicking Start extract
- **And** a scannable upload QR is shown

### Scenario: First upload starts convert without stopping receive

- **Given** Easy mode and an active Wi‑Fi receive session
- **When** the first file lands in `originals/`
- **Then** convert starts while extract remains **running**
- **And** Easy shows convert progress

### Scenario: View gallery when converted has files

- **Given** `converted/` contains at least one file
- **When** Easy mode is shown
- **Then** **View gallery** is visible
- **When** the user activates it
- **Then** the **Gallery** tab is shown

### Scenario: View gallery hidden when empty

- **Given** `converted/` is empty and convert is idle
- **When** Easy mode is shown
- **Then** **View gallery** is not shown

### Scenario: Gallery phone help on desktop

- **Given** the desktop app on the **Gallery** tab
- **When** the user taps the phone help control
- **Then** a popup shows gallery QR, LAN URL, and the upload-during-gallery note

### Scenario: Switch to Advanced during receive

- **Given** Easy mode with extract **running**
- **When** the user selects **Advanced**
- **Then** Step 1 shows the live upload QR
- **And** extract is still **running**

### Scenario: Advanced convert stops extract

- **Given** Advanced mode with extract **running** and files in `originals/`
- **When** the user clicks **Start convert**
- **Then** extract stops and convert runs (unchanged Advanced behavior)

## Out of scope

- Persisting `ui_mode` across app restarts
- Easy-mode error/invalid bucket review UI (use Advanced or OS folders)
- Changing conversion flags in Easy
