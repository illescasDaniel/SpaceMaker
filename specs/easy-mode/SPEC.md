# Easy mode (Photo backup)

## Metadata

- **Feature:** Photo backup module — Wi‑Fi upload QR, auto-receive, convert-as-received (when **Compress media** is on), **View gallery** when ready; phone gallery help on Gallery tab
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — Photo backup (`#view-easy`); phone upload [wireframes/phone-upload.html](../../wireframes/phone-upload.html). **Phone upload wireframe approved** 2026-09-23.
- **UX approved:** 2026-09-22 (initial Easy mode); **2026-09-23** (image import issue panels + open-folder actions); **2026-09-26** (**Compress media** preference + info panel)
- **Related:** [main-wizard](../main-wizard/SPEC.md), [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [gallery](../gallery/SPEC.md), [packaging](../packaging/SPEC.md)

## Triggers & routing

- **Entry:** Opened from Home hub → **Photo backup** tile (`active_module=photo_backup`, `ui_mode=easy`). **USB photo backup** tile opens the wizard (`ui_mode=advanced`). App launch defaults to **Home** hub — no auto Wi‑Fi until Photo backup is entered.
- **Session:** `ui_mode` is session-only (relaunch → Easy). Entering Home or another module does not imply an Easy↔Advanced toggle (USB is a separate module).
- **Header tabs:** **Home** (hub or active module) and **Gallery**. All shells follow the **OS light/dark** preference (`prefers-color-scheme` via shared `theme.css`); no per-module forced light/dark.
- **Easy bootstrap:** When the client loads Easy and extract is idle, the server starts **Wi‑Fi receive** automatically (library root from session defaults; no Start extract button).

## Visual & UI rules

### Easy (Photo backup layout)

- System light/dark tokens; generous spacing, centered column (~28rem).
- Vertical stack (centered, max ~28rem):
  1. **Large upload QR** (active Wi‑Fi session) with **ⓘ** just outside the QR (not overlapping); tap reveals the encoded upload URL and notes that users without a QR reader can open that URL in the phone browser (same Wi‑Fi). Breadcrumb **`Home / Photo backup`** at top (**Home** returns to hub).
  2. Short instruction: scan with phone on same Wi‑Fi
  3. **Library location line:** e.g. *Photos and videos are saved under `~/Pictures/SpaceMakerLibrary/`* (tilde display of session library root)
  4. **Compress media** preference row (see below) — between library location and Transfer
  5. **Transfer** progress (files received this session; total unknown → count + optional indeterminate bar while receiving)
  6. **Convert** progress — **only when Compress media is on** (same WebSocket convert job as Advanced). When idle with files already in `converted/`, status reads e.g. **1 file converted, waiting for more** (pluralized). When Compress media is **off**, hide Convert progress and show a short muted status: e.g. *Compression off — new uploads stay as received (no re-encode).*
  7. **Image import issues** (when any **and** Compress media is on): one or two **warning panels** (light theme, same warn styling as Advanced alerts), each shown only when its **image** count **> 0**:
     - **Unsupported:** heading e.g. *2 unsupported images*; hint that files are in the library **`invalid/`** folder and are **not** in the gallery; text action **Click here to open the invalid folder**.
     - **Failed convert:** heading e.g. *1 image failed to convert* (pluralized); hint that files are in **`error/`** (encode failed after retry); text action **Click here to open the error folder**.
     - When both counts are zero, or Compress media is off, the whole block is hidden (no placeholder).
     - Counts are **images only** (same semantics as today’s `image_import_issues` WebSocket field). No per-file list in Easy.
  8. **View gallery** button — **only when** `converted/` count **> 0**; switches to the **Gallery** tab (same as Main → Gallery).
  9. **Gallery tab (desktop):** circular **phone help** control (bottom-right); tap opens a popup with gallery LAN URL, QR, and *Please don't open this while uploading content.* (same information as the former Easy gallery block). Hidden on phone gallery shell.
- No library picker, connection toggle, or extract/convert buttons on Easy.
- Phone **upload** page (`/upload`): minimal; system theme via `theme.css`; footer hint varies for **iPhone vs Android** (UA detection). **iPhone:** single **Choose** button (no folder picker). **Android:** **Choose files** + **Choose folder**.
- Phone **gallery** (`/gallery` on device browser): dedicated mobile shell (no Easy/Advanced or Main/Gallery chrome); system theme via `theme.css` + `shell-gallery.css`. Server serves `gallery_mobile.html` for **private LAN** hosts; loopback/desktop app keeps full `index.html`.
- Phone **upload** page shows **files sent** count from `/api/upload/session` (`files_sent`).

### Compress media preference

- **Control:** checkbox labeled **Compress media**, with an **ⓘ** info button on the same row (same circular info control pattern as elsewhere).
- **Default when compression tools are available:** **checked (on)**.
- **When compression tools are unavailable:** checkbox is **unchecked**, **disabled**, and a short hint is shown under the row: e.g. *Compression tools are not available on this computer, so compress stays off.*
- **Info panel** (toggle via ⓘ; collapsed by default) copy, matching the approved wireframe:
  1. **Why:** Compress media to **save disk space** and keep photos and videos **web-compatible** for browsing in the gallery.
  2. **How:** photos convert to **AVIF**. Videos convert to **AV1** when this computer supports hardware encoding; otherwise they stay as received (or use H.264 hardware when available). Encode flags and routing remain those in [convert-media](../convert-media/SPEC.md) / [SpaceMaker-adaptations](../../docs/playbooks/SpaceMaker-adaptations.md) — Easy does not expose per-flag controls.
  3. **Persistence note:** Your choice is saved and reused the next time you open Photo backup.
- **Persistence:** the on/off choice is a **disk-backed user preference** restored on later app launches (unlike session-only `ui_mode`). If tools become unavailable on a later launch, the effective UI state is forced off + disabled for that session even if a prior “on” was stored; when tools return, restore the stored choice (default on if never set).
- **Tools available:** both `magick` and `ffmpeg` resolve via managed tools or `PATH` ([packaging](../packaging/SPEC.md) resolution order). Missing either → compression unavailable. Hardware video encoders are **not** required for the checkbox to be enabled (videos may move-as-is / use H.264 HW per convert-media).

### USB wizard layout

- Unchanged three-step wizard ([main-wizard](../main-wizard/SPEC.md)); same system theme as other modules. **Compress media** preference is Photo backup (Easy) only — Advanced Step 2 convert behavior is unchanged.

## API & actions

| Action | Behavior |
|--------|----------|
| Open invalid folder | `POST /api/library/open-folder` with body `{ "bucket": "invalid" }` — reveals `{library_root}/invalid/` in the OS file manager (create folder if missing). Same host adapter as gallery “open containing folder” ([main-wizard](../main-wizard/SPEC.md) Review default). |
| Open error folder | Same endpoint with `{ "bucket": "error" }` for `{library_root}/error/`. |
| Read/update Compress media | Preference is included in settings/session state exposed to the desktop client; toggling the checkbox persists immediately (or on change) via the settings/preference API. Exact field name is architecture detail; value is boolean. |
| Failure | Missing or non-writable library root → JSON error; client shows a short banner on Easy (same pattern as other Easy API errors). |

Allowed `bucket` values: `error`, `invalid` only (no path traversal; resolved under session library root).

## Convert while receiving (Easy only)

- Auto-convert runs **only when Compress media is on** and compression tools are available.
- After each completed Wi‑Fi upload (saved or size-skipped), if convert is **idle**, Compress media is **on**, and `originals/` is non-empty, start convert **without** stopping extract.
- When a convert batch finishes, if `originals/` still has files, Compress media is still on, and Easy concurrent policy applies, start another batch.
- **When Compress media is off:** do **not** start convert batches. New uploads remain in `originals/` (as received). An already-running convert job may finish its current batch; v1 does not require cancelling in-flight work. Turning Compress media **on** again with files still in `originals/` resumes Easy auto-convert when idle (same concurrent policy).
- **Advanced** **Start convert** still **stops extract first** then converts ([convert-media](../convert-media/SPEC.md)); Advanced ignores the Easy Compress media preference.

## Acceptance criteria (BDD)

### Scenario: Easy launches with upload QR

- **Given** SpaceMaker starts with default library root
- **When** the client opens Easy mode
- **Then** Wi‑Fi extract is **running** without clicking Start extract
- **And** a scannable upload QR is shown

### Scenario: Compress media defaults on when tools available

- **Given** compression tools (`magick` and `ffmpeg`) are available
- **And** the user has never saved a Compress media preference
- **When** Photo backup (Easy) is shown
- **Then** **Compress media** is checked and enabled
- **And** Convert progress is shown (not the compression-off status)

### Scenario: Compress media forced off when tools unavailable

- **Given** `magick` or `ffmpeg` cannot be resolved
- **When** Photo backup (Easy) is shown
- **Then** **Compress media** is unchecked and disabled
- **And** the tools-unavailable hint is visible
- **And** Convert progress is hidden
- **And** the compression-off status is shown
- **And** Easy does not auto-start convert after uploads

### Scenario: Info panel explains why and how

- **Given** Photo backup (Easy) is shown
- **When** the user activates the Compress media ⓘ control
- **Then** an info panel is shown that states compressing saves disk space and keeps media web-compatible
- **And** the panel states photos convert to AVIF and videos to AV1 when hardware encoding is available
- **And** the panel notes that the choice is saved for future Photo backup opens

### Scenario: User turns Compress media off

- **Given** Easy mode with Compress media on and tools available
- **When** the user unchecks **Compress media**
- **Then** the preference is persisted
- **And** Convert progress is hidden
- **And** the compression-off status is shown
- **And** further uploads do not start a new convert batch

### Scenario: Preference restored on relaunch

- **Given** the user previously turned Compress media off while tools were available
- **When** the app relaunches and Photo backup (Easy) is shown
- **And** compression tools are still available
- **Then** **Compress media** is unchecked
- **And** Easy does not auto-start convert

### Scenario: First upload starts convert without stopping receive

- **Given** Easy mode, Compress media **on**, tools available, and an active Wi‑Fi receive session
- **When** the first file lands in `originals/`
- **Then** convert starts while extract remains **running**
- **And** Easy shows convert progress

### Scenario: Upload with Compress media off leaves originals

- **Given** Easy mode with Compress media **off** and an active Wi‑Fi receive session
- **When** a file lands in `originals/`
- **Then** convert does not start
- **And** the file remains in `originals/`

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

### Scenario: No import issue panels when buckets empty

- **Given** Easy mode with Compress media on and `image_import_issues.errors` and `image_import_issues.invalid` are both **0**
- **When** Easy mode is shown
- **Then** the image import issues block is not visible

### Scenario: Unsupported images panel

- **Given** Easy mode with Compress media on and at least one **image** in library `invalid/`
- **When** Easy mode is shown
- **Then** the unsupported-images warning panel is visible with the correct count
- **And** the hint mentions `invalid/` and that files are not in the gallery

### Scenario: Failed convert panel

- **Given** Easy mode with Compress media on and at least one **image** in library `error/` and zero images in `invalid/`
- **When** Easy mode is shown
- **Then** only the failed-convert warning panel is visible
- **And** the unsupported panel is not shown

### Scenario: Import issue panels hidden when Compress media off

- **Given** Easy mode with Compress media **off** and non-zero `image_import_issues` counts
- **When** Easy mode is shown
- **Then** the image import issues block is not visible

### Scenario: Open invalid folder from Easy

- **Given** the unsupported-images panel is visible
- **When** the user activates **Click here to open the invalid folder**
- **Then** the OS file manager opens (or focuses) the library `invalid/` directory

### Scenario: Open error folder from Easy

- **Given** the failed-convert panel is visible
- **When** the user activates **Click here to open the error folder**
- **Then** the OS file manager opens (or focuses) the library `error/` directory

## Out of scope

- Persisting `ui_mode` across app restarts
- Easy-mode per-file filenames or in-app file list (folder reveal only)
- **Move to converted** from Easy (Advanced Step 2 only)
- Editing encode flags / quality / codec priority in Easy (fixed per [convert-media](../convert-media/SPEC.md))
- Applying Compress media preference to USB wizard / Advanced Step 2
- Cancelling an in-flight convert batch when the user turns Compress media off (v1 may let the current batch finish)
- Auto-moving `originals/` into `converted/` when Compress media is off (files stay in `originals/` until compress/convert runs)

## Testing strategy

| Layer | Focus |
|-------|--------|
| Unit | Easy import panel visibility from `image_import_issues` counts (zero → hidden; partial → one or two panels); Compress media default / tools-unavailable forced off; auto-convert gated on preference |
| Integration | `POST /api/library/open-folder` resolves `error` / `invalid` under session library root; rejects unknown bucket; preference persists across simulated relaunch |
