# Main wizard (Extract → Convert → Visualize)

## Metadata

- **Feature:** Primary desktop/web UI inside pywebview
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — Easy (default) + Advanced wizard
- **Related specs:** [easy-mode](../easy-mode/SPEC.md), [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [gallery](../gallery/SPEC.md)
- **Transport:** HTTP for pages/API; WebSockets for extract and convert progress

## Triggers & routing

- **Entry:** User launches SpaceMaker (`desktop.py` opens pywebview → local FastAPI origin).
- **Default view:** **Easy** mode ([easy-mode](../easy-mode/SPEC.md)) — light UI, auto Wi‑Fi receive, convert-as-received. **Advanced** is the three-step wizard (cards 1–3). Header toggle **Easy | Advanced** (session-only; relaunch → Easy). Gallery is a separate tab or route `/gallery`; gallery chrome follows active mode theme (light in Easy, dark in Advanced).
- **Step gating (UX):**
  - **Start convert** is **disabled** when **`originals/` has zero files** (recursive count) or convert is already **running**.
  - **Start convert** is **enabled** when `originals/` has at least one file, **including while extract is `running` or `paused`**.
  - When the user clicks **Start convert** during an active extract, the server **gracefully stops extract** (same rules as **Stop extract**: finish in-flight file/upload, then end the session/queue), **waits** for extract to finish stopping, then **starts convert** on files already in `originals/`.
  - Step 3 **Visualize** card is **disabled** only when `converted/` is empty **and** convert is not running (no gallery to show yet).
  - Step 3 is **enabled** when `converted/` file count **> 0** (including media from a previous session before this launch) **or** convert is **running** / **completed**.
  - **Open gallery**, LAN URL, and QR are available whenever Step 3 is enabled.
  - SPA routing: `GET /gallery` loads the app and **activates the Gallery view** (not the wizard). Tab switches and **Open gallery** update the browser path (`/` vs `/gallery`) via History API.
- **Exit:** User closes desktop window; background jobs should honor pause/cancel where implemented (pause: extract first; convert pause: out of scope v1 unless noted in extract spec).

## Visual & UI rules

- Match wireframe structure: header **SpaceMaker**, three cards on wide viewports, stacked on narrow.
- Each card shows: step number, title, **status line** (`Not started` | `In progress: N%` | `Completed: N files` | `Waiting for …` | `Failed`), progress bar when applicable.
- **Step 1 — Extract:** **connection method** segmented control (**Wi‑Fi** default, **MTP**, **ADB (cable)**) with a **visible container border** (see wireframe), **info (ⓘ)** button, library root picker, Copy/Move mode chips (**label text uses `--text`**, readable on dark background), **Start extract**, **Pause extract**, **Resume extract** (while paused), **Stop extract**, file counts.
- **Step 1 — Wi‑Fi:** hide USB **device picker**, **device status**, and **source folder** checklist. Show **phone upload** block: idle hint until extract starts; while **running** or **paused**, show LAN **URL + QR** for the **upload page** (not the gallery URL). **Move** chip is **disabled**; only **Copy** applies (uploads always copy into `originals/`).
- **Step 1 — USB (MTP/ADB):** **device picker** + **status line** (friendly copy + connection indicator — never raw `libmtp:0`-style ids as the main message), **source folder** checklist, Copy/Move chips (Move enabled when cable method selected).
- **Step 1 — Extract controls (enabled/disabled):**
  | Extract phase | Start | Pause | Resume | Stop |
  |---------------|-------|-------|--------|------|
  | Idle (ready) | enabled | **disabled** | hidden/disabled | disabled |
  | Running | **disabled** | enabled | hidden/disabled | enabled |
  | Paused | disabled | hidden/disabled | enabled | enabled |
  | Stopped / completed / error | enabled | disabled | hidden/disabled | disabled |
- **Step 1 — Accessibility:** form controls (`select`, `input`) use **`--text`** on **`--surface2`** backgrounds (readable contrast on dark theme).
- **Step 2 — Convert:** one-line policy summary (AVIF/AV1, files leave `originals/`), **Start convert** button (enabled when `originals/` non-empty — see step gating), progress bar.
- **Warnings (Step 2 area):**
  - **Error bucket:** rendered **only** when `error/` file count **> 0**. When count is **0**, the warning block is **not in the DOM** or is **hidden** with no placeholder — users must not see an empty warning.
  - **Invalid bucket:** same rule for `invalid/` count **> 0** only.
  - When visible: warning styling; error — **Review**, **Move to converted**; invalid — **Review** only.
- **Step 3 — Visualize:** status line (`Not started` | `In progress: N%` | `Ready: N files`), LAN URL field, **scannable QR** encoding the same URL, **Open gallery** button.
- **Step 3 status rules:**
  - `Not started` — `converted/` count is 0 and convert is idle.
  - `In progress: N%` — convert job is running (same percent as Step 2).
  - `Ready: N files` — `converted/` count **> 0** (N = recursive file count).
- Real-time progress: WebSocket messages update percent and counts without full page reload.
- **Global footer:** on every main view, a persistent footer with link **About & Legal** opens a **mini page** (scrollable in-app route, e.g. `/about` or overlay — not a top-level wizard tab). Wireframe: [wireframes/app.html](../../wireframes/app.html) footer + `#view-legal`. **UX approved** (2026-09-22).
- **About & Legal page content:** Privacy summary + contact email, third-party tool names with **external home page links**, disclaimer summary (backups, no liability). Production loads full markdown from bundled `docs/legal/` (same sections).

## Acceptance criteria (BDD)

### Scenario: Initial wizard state

- **Given** SpaceMaker has just started and no jobs ran yet
- **When** the main wizard is shown
- **Then** Step 1 shows device detection state (connected or “No device”)
- **And** connection method defaults to **Wi‑Fi**
- **And** Step 1 status is `Not started`
- **And** Step 2 shows `Waiting for extract to finish` or equivalent when extract not complete
- **And** Step 3 shows `Not started` when `converted/` is empty
- **And** Step 3 card is disabled when `converted/` is empty and convert is idle

### Scenario: Visualize ready when converted already has files

- **Given** SpaceMaker starts and `converted/` already contains at least one file (e.g. from a previous session)
- **When** the main wizard is shown
- **Then** Step 3 status is `Ready: N files` (N > 0)
- **And** Step 3 card is not disabled
- **And** **Open gallery** is enabled

### Scenario: Gallery URL route

- **Given** the local server is running
- **When** the user navigates to `/gallery` (desktop or phone on LAN)
- **Then** the Gallery view is shown (timeline or last-selected organization mode)
- **And** the Main wizard tab is not the active view

### Scenario: Connection method info

- **Given** the user is on Step 1
- **When** the user opens the connection method info control
- **Then** instructions for Wi‑Fi, MTP, and ADB (cable) are visible
- **And** Wi‑Fi help covers same network, Start extract, QR scan, and that Move is unavailable
- **And** MTP help focuses on phone USB mode, not installing libmtp on Windows/Linux

### Scenario: Extract progress updates over WebSocket

- **Given** an extract job is running
- **When** the server emits progress events
- **Then** Step 1 status shows `In progress: N%`
- **And** the progress bar and file count (`done / total`) update

### Scenario: Extract completion enables convert

- **Given** extract has completed successfully and `originals/` contains at least one file
- **When** the wizard refreshes step state
- **Then** Step 1 status is `Completed: N files`
- **And** Step 2 **Start convert** is enabled

### Scenario: Convert during active extract stops extract first

- **Given** extract is **running** or **paused** and `originals/` contains at least one file
- **When** the wizard refreshes step state
- **Then** Step 2 **Start convert** is enabled
- **When** the user clicks **Start convert**
- **Then** extract enters **stopped** (Wi‑Fi upload session invalidated; USB queue aborted after current file)
- **And** convert starts on files in `originals/`

### Scenario: Convert disabled when originals empty

- **Given** extract is not running and `originals/` is empty
- **When** the wizard refreshes step state
- **Then** Step 2 **Start convert** is disabled

### Scenario: Device status is user-friendly

- **Given** a device is connected for the selected method
- **When** Step 1 is shown
- **Then** status shows a readable name and **Connected via MTP** or **Connected via ADB**
- **And** device status is hidden when **Wi‑Fi** is selected
- **And** a green (or success) indicator is shown
- **And** internal backend identifiers are not used as the primary status string

### Scenario: Bucket warnings hidden at zero

- **Given** `error/` and `invalid/` are both empty
- **When** Step 2 is displayed
- **Then** no error or invalid warning panels are visible

### Scenario: Pause, resume, and stop extract (UI)

- **Given** extract is **idle**
- **Then** **Pause extract** is disabled
- **And** **Start extract** is enabled (when library root is valid and, for USB, device and folders are valid)

### Scenario: Wi‑Fi extract shows upload QR while receiving

- **Given** **Wi‑Fi** is selected and the user clicked **Start extract**
- **When** extract is **running**
- **Then** Step 1 shows a scannable QR and URL for the phone **upload** page
- **And** the URL includes a session token valid until **Stop extract**
- **And** **Move** is disabled

### Scenario: Wi‑Fi idle before Start

- **Given** **Wi‑Fi** is selected and extract is **idle**
- **When** Step 1 is shown
- **Then** the upload QR is not active (placeholder or hidden)
- **And** **Start extract** is enabled when library root is valid

- **Given** extract is running
- **Then** **Start extract** is disabled
- **And** **Pause extract** is enabled
- **When** the user clicks **Pause extract**
- **Then** **Resume** and **Stop** are available and **Start** is not
- **When** the user clicks **Stop extract**
- **Then** extract ends in a stopped state and **Start extract** is available again

### Scenario: Convert progress updates over WebSocket

- **Given** a convert job is running
- **When** the server emits progress events
- **Then** Step 2 status shows `In progress: N%`
- **And** the progress bar updates

### Scenario: Error folder warning

- **Given** at least one file exists under `error/`
- **When** the wizard is displayed
- **Then** an error warning shows the file count
- **And** **Review** is available
- **And** **Move to converted** is available

### Scenario: User moves error files to converted

- **Given** files exist in `error/`
- **When** the user clicks **Move to converted**
- **Then** each file is moved to `converted/` preserving relative paths
- **And** `error/` is empty
- **And** the error warning is hidden

### Scenario: Invalid folder warning

- **Given** at least one file exists under `invalid/`
- **When** the wizard is displayed
- **Then** an invalid warning shows the file count and review suggestion
- **And** **Review** is available
- **And** there is no “move all to converted” action for invalid files

### Scenario: Visualize shows LAN access

- **Given** the local server is bound to a LAN interface
- **When** Step 3 is visible
- **Then** a gallery URL with host IP and port is shown
- **And** a scannable QR code encodes that URL (not plain host:port text)

### Scenario: Footer opens About and Legal

- **Given** the user is on the wizard or gallery
- **When** they click **About & Legal** in the footer
- **Then** the mini legal page is shown with Privacy, Third-party tools, and Disclaimer sections
- **And** **Back** returns to the previous main view

### Scenario: Open gallery from Step 3

- **Given** `converted/` contains at least one file
- **When** the user clicks **Open gallery**
- **Then** the gallery view opens (same window navigation or tab per wireframe)

## Failure scenarios

| Condition | Expected UI |
|-----------|-------------|
| No device for selected USB method | Step 1 shows not connected (muted indicator + setup hint); Start disabled or clear error on attempt |
| Wi‑Fi session ended or invalid token on phone | Upload page shows session ended; user must Start extract again on PC |
| Missing host dependency (adb, libmtp) | Step 1 banner with install hint from info panel |
| Library root not writable | Error message on Step 1; no silent failure |
| WebSocket disconnect during job | Status shows reconnecting or last known progress; job continues server-side |
| Review clicked | OS file manager or in-app list opens `error/` or `invalid/` path (implementation choice; must be spec’d in adapter — default: reveal folder in OS file manager) |

## Validation rules (UI/API)

- Library root must be an absolute path chosen by user (folder picker).
- Copy/Move mode is exclusive; default **Copy**.
- Connection method: default **Wi‑Fi**; only one active per extract job.
- **Wi‑Fi:** Move mode is not offered; API rejects Move if method is Wi‑Fi.
- Warning counts must reflect live filesystem scans or cached counts updated after convert/extract completes.

## Testing strategy

| Layer | Focus |
|-------|--------|
| Unit | Step state machine: given extract/convert phase + folder counts → enabled buttons and status strings |
| Unit | Visualize step: given `converted` count + convert phase → status text and card enabled flag |
| Unit | Warning visibility from `FileSystem` port listing `error/` / `invalid/` (zero → hidden) |
| Unit | Convert button: disabled when `originals/` empty; start convert stops active extract first |
| Integration | WebSocket handler emits progress DTOs; one client receives ordered updates (mock use case) |
| Integration | HTTP tests use **`httpx2`** (not legacy `httpx` + Starlette TestClient) so pytest emits **no** Starlette/anyio deprecation warnings |
| Out of scope v1 | Automated browser/E2E; visual regression |

## Out of scope

- Cloud backup or accounts
- iOS **USB** extract (Android-first cable path; **Wi‑Fi upload** supports iPhone browser — see extract spec)
- Editing conversion settings in UI (flags fixed per reference script)
- **taskipy** `spacemaker` run task (dev ergonomics — tracked in `pyproject.toml`, not a product spec)
- In-app media viewer on wizard screen
