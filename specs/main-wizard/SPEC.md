# Main wizard (Extract → Convert → Visualize)

## Metadata

- **Feature:** Primary desktop/web UI inside pywebview
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — tab “Main wizard”
- **Related specs:** [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [gallery](../gallery/SPEC.md)
- **Transport:** HTTP for pages/API; WebSockets for extract and convert progress

## Triggers & routing

- **Entry:** User launches SpaceMaker (`desktop.py` opens pywebview → local FastAPI origin).
- **Default view:** Three-step wizard (cards 1–3). Gallery is a separate view (top tab or route `/gallery`; wireframe uses tabs).
- **Step gating (UX):**
  - **Start convert** is **disabled** when extract is **`running`** or **`paused`**, or when **`originals/` has zero files** (recursive count).
  - **Start convert** is **enabled** when extract is **not** active (`idle`, `completed`, `stopped`, or `error`) **and** `originals/` has at least one file (including after a partial extract or a previous run).
  - Step 3 disabled until convert has run at least once to completion **or** user opens gallery when `converted/` is non-empty (manual “Open gallery” always allowed if `converted/` has media).
- **Exit:** User closes desktop window; background jobs should honor pause/cancel where implemented (pause: extract first; convert pause: out of scope v1 unless noted in extract spec).

## Visual & UI rules

- Match wireframe structure: header **SpaceMaker**, three cards on wide viewports, stacked on narrow.
- Each card shows: step number, title, **status line** (`Not started` | `In progress: N%` | `Completed: N files` | `Waiting for …` | `Failed`), progress bar when applicable.
- **Step 1 — Extract:** **connection method** segmented control (**MTP** default, **ADB (recommended)**) with a **visible container border** (see wireframe), **info (ⓘ)** button, **device picker** + **status line** (friendly copy + connection indicator — never raw `libmtp:0`-style ids as the main message), **source folder** checklist, library root picker, Copy/Move mode chips (**label text uses `--text`**, readable on dark background), **Start extract**, **Pause extract**, **Resume extract** (while paused), **Stop extract**, file counts.
- **Step 1 — Extract controls (enabled/disabled):**
  | Extract phase | Start | Pause | Resume | Stop |
  |---------------|-------|-------|--------|------|
  | Idle (ready) | enabled | **disabled** | hidden/disabled | disabled |
  | Running | **disabled** | enabled | hidden/disabled | enabled |
  | Paused | disabled | hidden/disabled | enabled | enabled |
  | Stopped / completed / error | enabled | disabled | hidden/disabled | disabled |
- **Step 1 — Accessibility:** form controls (`select`, `input`) use **`--text`** on **`--surface2`** backgrounds (readable contrast on dark theme).
- **Step 2 — Convert:** one-line policy summary (AVIF/AV1, files leave `originals/`), **Start convert** button (disabled while Step 1 extract is **running** or **paused** — see step gating above), progress bar.
- **Warnings (Step 2 area):**
  - **Error bucket:** rendered **only** when `error/` file count **> 0**. When count is **0**, the warning block is **not in the DOM** or is **hidden** with no placeholder — users must not see an empty warning.
  - **Invalid bucket:** same rule for `invalid/` count **> 0** only.
  - When visible: warning styling; error — **Review**, **Move to converted**; invalid — **Review** only.
- **Step 3 — Visualize:** LAN URL field, QR code for same URL, **Open gallery** button.
- Real-time progress: WebSocket messages update percent and counts without full page reload.
- **Global footer:** on every main view, a persistent footer with link **About & Legal** opens a **mini page** (scrollable in-app route, e.g. `/about` or overlay — not a top-level wizard tab). Wireframe: [wireframes/app.html](../../wireframes/app.html) footer + `#view-legal`. **UX approved** (2026-09-22).
- **About & Legal page content:** Privacy summary + contact email, third-party tool names with **external home page links**, disclaimer summary (backups, no liability). Production loads full markdown from bundled `docs/legal/` (same sections).

## Acceptance criteria (BDD)

### Scenario: Initial wizard state

- **Given** SpaceMaker has just started and no jobs ran yet
- **When** the main wizard is shown
- **Then** Step 1 shows device detection state (connected or “No device”)
- **And** connection method defaults to **MTP**
- **And** Step 1 status is `Not started`
- **And** Step 2 shows `Waiting for extract to finish` or equivalent when extract not complete
- **And** Step 3 shows `Not started` when `converted/` is empty

### Scenario: Connection method info

- **Given** the user is on Step 1
- **When** the user opens the connection method info control
- **Then** instructions for MTP and ADB (recommended) are visible
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

### Scenario: Convert stays disabled during extract

- **Given** extract is **running** or **paused**
- **When** the wizard refreshes step state
- **Then** Step 2 **Start convert** is disabled
- **And** status explains waiting for extract (or equivalent)

### Scenario: Convert disabled when originals empty

- **Given** extract is not running and `originals/` is empty
- **When** the wizard refreshes step state
- **Then** Step 2 **Start convert** is disabled

### Scenario: Device status is user-friendly

- **Given** a device is connected for the selected method
- **When** Step 1 is shown
- **Then** status shows a readable name and **Connected via MTP** or **Connected via ADB**
- **And** a green (or success) indicator is shown
- **And** internal backend identifiers are not used as the primary status string

### Scenario: Bucket warnings hidden at zero

- **Given** `error/` and `invalid/` are both empty
- **When** Step 2 is displayed
- **Then** no error or invalid warning panels are visible

### Scenario: Pause, resume, and stop extract (UI)

- **Given** extract is **idle**
- **Then** **Pause extract** is disabled
- **And** **Start extract** is enabled (when device and folders are valid)

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
- **And** a QR code encodes that URL

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
| No device for selected method | Step 1 shows not connected (muted indicator + setup hint); Start disabled or clear error on attempt |
| Missing host dependency (adb, libmtp) | Step 1 banner with install hint from info panel |
| Library root not writable | Error message on Step 1; no silent failure |
| WebSocket disconnect during job | Status shows reconnecting or last known progress; job continues server-side |
| Review clicked | OS file manager or in-app list opens `error/` or `invalid/` path (implementation choice; must be spec’d in adapter — default: reveal folder in OS file manager) |

## Validation rules (UI/API)

- Library root must be an absolute path chosen by user (folder picker).
- Copy/Move mode is exclusive; default **Copy**.
- Connection method: default **MTP**; only one active per extract job.
- Warning counts must reflect live filesystem scans or cached counts updated after convert/extract completes.

## Testing strategy

| Layer | Focus |
|-------|--------|
| Unit | Step state machine: given extract/convert phase + folder counts → enabled buttons and status strings |
| Unit | Warning visibility from `FileSystem` port listing `error/` / `invalid/` (zero → hidden) |
| Unit | Convert button: disabled when extract active or `originals/` empty |
| Integration | WebSocket handler emits progress DTOs; one client receives ordered updates (mock use case) |
| Integration | HTTP tests use **`httpx2`** (not legacy `httpx` + Starlette TestClient) so pytest emits **no** Starlette/anyio deprecation warnings |
| Out of scope v1 | Automated browser/E2E; visual regression |

## Out of scope

- Cloud backup or accounts
- iOS device extract (Android-first; connection details in extract spec)
- Editing conversion settings in UI (flags fixed per reference script)
- **taskipy** `spacemaker` run task (dev ergonomics — tracked in `pyproject.toml`, not a product spec)
- In-app media viewer on wizard screen
