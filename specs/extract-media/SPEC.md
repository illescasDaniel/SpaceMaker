# Extract media (device → originals/)

## Metadata

- **Feature:** Copy or move photos/videos from connected Android device into library `originals/`
- **Use case:** `ExtractMedia`
- **Ports:** `DeviceRepository` (outbound), `FileSystem` (outbound)
- **UI:** [main-wizard](../main-wizard/SPEC.md) Step 1
- **Packaging:** Bundled native tools — [packaging/SPEC.md](../packaging/SPEC.md)

## Connection method (MTP vs ADB)

| Method | UI label | Default | Notes |
|--------|----------|---------|--------|
| **MTP** | `MTP` | **Yes** | USB file transfer mode; no USB debugging required. Easiest for most users. |
| **ADB** | `ADB (recommended)` | No | Faster/reliable for power users; requires USB debugging + authorized device. |

- User selects exactly one method via a **simple control** (segmented toggle or radio group) on Step 1.
- Selection is persisted for the session (optional: last choice in local settings file — v1 session-only is OK).
- Changing method while idle **re-runs device detection** for that backend.
- Extract must not start if the chosen backend reports no device (unless user explicitly picks a mounted MTP volume — see detection).

### Platform tooling (adapters)

**MTP (users vs app):** On Windows and Linux, MTP is already “native” for humans (Explorer, Nautilus/Dolphin, etc.). Users only need **File transfer / MTP** on the phone. They do **not** need to install libmtp manually on those OSes for normal use.

**MTP (app):** SpaceMaker needs a programmatic MTP client. Use **libmtp** (same stack on **Windows, Linux, and macOS**) in `MtpDeviceRepository` — CLI tools (`mtp-detect`, `mtp-getfile`, …) or a thin binding. Packaged builds should **bundle or ship** libmtp tools where licensing allows (PyInstaller side-by-side); dev machines install libmtp via package manager.

| OS | MTP (SpaceMaker adapter) | ADB adapter |
|----|--------------------------|-------------|
| **All** | **libmtp** (one code path), **bundled** in release builds | [adbutils](https://github.com/openatx/adbutils) + **bundled** platform-tools `adb` |

- **Packaged app:** Ship the correct `adb` (and libmtp tools) per **OS + CPU** inside the installer/binary — see [packaging/SPEC.md](../packaging/SPEC.md). Users do not install Android SDK platform-tools.
- **Dev:** `uv run` may fall back to `adb` / libmtp on `PATH` when bundle absent.
- **Not** primary v1: Windows WPD COM-only adapter, macOS gphoto2-only path (optional fallback later if libmtp fails on a device).
- **Domain/application** depend only on `DeviceRepository` — never import adbutils or libmtp directly.
- Adapter resolves bundled binary path via bootstrap; missing bundled tools in **frozen** builds = hard error with support hint.
- Unit tests use fakes; integration tests mock subprocess/adbutils.

### Info button (help content)

An **info** control (ⓘ) beside the connection method opens a panel or modal with:

1. **MTP:** plug phone → unlock → choose **File transfer / MTP** (not “charge only”). No extra desktop install on Windows/Linux for typical use; on macOS, USB MTP is less automatic — troubleshooting may mention libmtp if the app reports a missing bundled tool.
2. **ADB (recommended):** Developer options → USB debugging → accept RSA prompt on phone. **No separate adb install** in packaged SpaceMaker (adb is bundled); dev builds may use system `adb` on PATH.

Copy is concise; link to future docs page optional.

## Source folders (device scope)

Users choose **which device folders** to include before extract. v1 uses a **multi-select checklist** on Step 1 (not a free-text path editor).

| Folder (label) | Typical device path (ADB) | Default |
|----------------|---------------------------|---------|
| **Camera (DCIM)** | `/sdcard/DCIM`, `/storage/emulated/0/DCIM` | On |
| **Pictures** | `/sdcard/Pictures`, … | On |
| **Movies** | `/sdcard/Movies`, … | On |

- At least **one** folder must remain selected; **Start extract** is disabled when none are selected.
- Selection is **session-scoped** (persist with other Step 1 settings for the running app).
- **MTP:** adapter maps the same labels to paths under the mounted volume (relative paths under the GVFS/libmtp root).
- **Queue:** `list_media_paths` (or equivalent) returns only files under selected roots; order remains deterministic (sorted path).
- Changing folder selection while extract is **idle** updates the next job’s file list; changing it during **running** or **paused** is disabled until the job stops.

## Triggers & routing

- **Start:** User selects library root, **connection method**, **source folders**, Copy or Move mode, connected device, clicks **Start extract**.
- **Pause:** User clicks **Pause extract** — finish the **current file** transfer, then enter **`paused`**; no new files start until **Resume**.
- **Resume:** From **`paused`**, continue the same queue from the next pending file.
- **Stop:** User clicks **Stop extract** — finish the **current file** if one is in flight, then **abort** the queue; state becomes **`stopped`**; completed/skipped files remain in `originals/`; user may **Start extract** again (idempotent skip rules apply).
- **Completion:** All queued device files processed, user **Stop**, or unrecoverable device error.

## Library layout

On first extract to a library root, ensure directories exist:

- `originals/`
- `converted/`
- `error/`
- `invalid/`

Extract **only** writes into `originals/`, preserving relative paths from device media layout (implementation defines mapping; paths must be stable across runs).

## Idempotency & fault tolerance

For each file on device:

1. Compute destination path under `originals/`.
2. If destination **exists** and **size matches** source (and optional checksum if implemented), **skip** transfer (count as success).
3. If destination exists but size differs, **re-transfer** (overwrite) — v1: delete partial dest then re-copy.
4. If transfer interrupted mid-run, re-run extract skips completed files per rule 2.

Checksum optional v1: size-only is acceptable if spec tests cover size match.

## Copy vs Move

| Mode | Device after success | PC `originals/` |
|------|----------------------|-----------------|
| Copy | File remains | File present |
| Move | File removed from device | File present |

Move requires backend support (**ADB** usually supports delete; **MTP** may not — if delete fails, log error, keep PC copy, count file as failed move).

## Acceptance criteria (BDD)

### Scenario: Default connection method is MTP

- **Given** the user opens Step 1 for the first time in a session
- **When** the extract form is shown
- **Then** **MTP** is selected
- **And** **ADB (recommended)** is available as the alternate option

### Scenario: User switches to ADB and refreshes detection

- **Given** the user is on Step 1 with MTP selected and no MTP device
- **When** the user selects **ADB (recommended)**
- **Then** device status is refreshed using the ADB backend
- **And** an authorized ADB device shows as connected when present

### Scenario: Info button explains setup

- **Given** the user is on Step 1
- **When** the user activates the connection method **info** control
- **Then** help text is shown for both MTP and ADB
- **And** the text does not ask Windows/Linux users to install libmtp for everyday use
- **And** adb authorization steps are included for ADB

### Scenario: Device detected via MTP

- **Given** MTP is selected and a phone is mounted via MTP
- **When** extract UI loads device status
- **Then** a **human-readable device name** is shown (e.g. phone model or MTP volume label)
- **And** a **connected** indicator (e.g. green status dot) is visible
- **And** raw backend ids (e.g. `libmtp:0`, GVFS mount paths) are **not** shown as the primary status text

### Scenario: Device detected via ADB

- **Given** ADB (recommended) is selected and adb reports one authorized device
- **When** extract UI loads device status
- **Then** device model or a friendly label is shown with **connected** indicator
- **And** the device picker shows friendly labels, not bare serials unless no model is available

### Scenario: User selects source folders

- **Given** Step 1 is idle and at least one device folder exists on the backend
- **When** the user unchecks all source folders
- **Then** **Start extract** is disabled
- **When** the user checks **Camera (DCIM)** only
- **Then** the next extract queue includes only media under that folder scope

### Scenario: Pause and resume extract

- **Given** extract is **running** with multiple files pending
- **When** the user clicks **Pause extract**
- **Then** the in-flight file completes
- **And** extract enters **`paused`** with no further files started
- **When** the user clicks **Resume extract**
- **Then** extract continues from the next pending file

### Scenario: Stop extract safely

- **Given** extract is **running** or **paused**
- **When** the user clicks **Stop extract**
- **Then** the in-flight file completes if any
- **And** extract enters **`stopped`**
- **And** files already in `originals/` are unchanged
- **And** a later **Start extract** skips completed files per idempotency rules

### Scenario: No device for selected method

- **Given** the selected backend reports no device
- **When** the user attempts Start extract
- **Then** extract does not start
- **And** user sees a clear error naming the active method (MTP or ADB)

### Scenario: Copy file to originals

- **Given** Copy mode and a device file not yet in `originals/`
- **When** extract processes the file
- **Then** the file appears under `originals/` with matching size
- **And** the file remains on the device

### Scenario: Move file to originals via ADB

- **Given** Move mode, ADB backend, and successful transfer
- **When** extract completes for that file
- **Then** the file is in `originals/`
- **And** the file is removed from the device via ADB

### Scenario: Skip already transferred file

- **Given** a file already in `originals/` with same size as device source
- **When** extract runs again
- **Then** the file is skipped
- **And** progress counts it as completed

### Scenario: Progress reporting

- **Given** extract is running
- **When** each file completes or skips
- **Then** progress percent and `completed / total` update via WebSocket

### Scenario: Creates library folders

- **Given** a new empty library root
- **When** extract starts
- **Then** `originals/`, `converted/`, `error/`, and `invalid/` exist

## Failure scenarios

| Failure | Behavior |
|---------|----------|
| Wrong method (MTP selected but only ADB available) | Status “No device”; info points user to switch method or fix setup |
| Missing host tool (no libmtp on macOS, no adb) | Block Start; message names missing dependency |
| Device disconnect mid-transfer | Pause with error; completed files remain; retry skips done files |
| Disk full | Fail current file; surface error |
| Permission denied on library root | Fail before transfer batch |
| Single file read error on device | Skip file, increment failed count, continue batch (v1) |
| Move unsupported on MTP | That file fails move; copy already on PC is kept |

## Validation rules

- Library root must be writable.
- Connection method must be `mtp` or `adb` (internal enum); UI labels as above.
- Extract uses the repository implementation matching the selected method for the whole job (no mixing backends mid-run).
- **Source folders:** at least one selected; enum keys stable for API (`dcim`, `pictures`, `movies` — exact names in ports/UI DTO).
- **Job control:** only one extract job active; Pause/Resume/Stop apply to the active job; Stop is idempotent if already stopped.

## Testing strategy

| Layer | Tests |
|-------|--------|
| Unit | Idempotency: existing dest size → skip |
| Unit | Copy vs Move calls correct `DeviceRepository` methods |
| Unit | Factory selects fake MTP vs fake ADB repo from user choice |
| Unit | Progress callback once per terminal file state |
| Unit | Pause/stop: given running queue → pause stops after current file; stop leaves partial progress |
| Unit | Folder filter: only paths under selected roots enter queue |
| Integration | Mock libmtp/adbutils boundaries; `tmp_path` filesystem |
| Out of scope CI | Real devices, real adb on CI |

## Out of scope

- iPhone / iOS extract
- Wi‑Fi ADB (follow-up)
- Per-album or arbitrary path picker (beyond the v1 folder checklist)
- Encrypting `originals/` at rest
