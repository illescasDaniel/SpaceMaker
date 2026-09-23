# Extract media (device → originals/)

## Metadata

- **Feature:** Copy or move photos/videos into library `originals/` via **Wi‑Fi phone upload** (default), **MTP**, **ADB**, or **iPhone (USB)** (AFC on Linux)
- **Wireframes:** [wireframes/app.html](../../wireframes/app.html) Step 1; phone page [wireframes/phone-upload.html](../../wireframes/phone-upload.html)
- **Use case:** `ExtractMedia`
- **Ports:** `DeviceRepository` (outbound), `FileSystem` (outbound)
- **UI:** [main-wizard](../main-wizard/SPEC.md) Step 1
- **Packaging:** Bundled native tools — [packaging/SPEC.md](../packaging/SPEC.md)

## Connection method (Wi‑Fi, MTP, ADB, iPhone USB)

| Method | UI label | Default | Notes |
|--------|----------|---------|--------|
| **Wi‑Fi** | `Wi‑Fi` | **Yes** | No cable. Phone browser on same LAN uploads files during an extract **session**. Does not use `DeviceRepository`. |
| **MTP** | `MTP` | No | USB file transfer mode; no USB debugging required. |
| **ADB** | `ADB (cable)` | No | USB; requires USB debugging + authorized device. |
| **AFC** | `iPhone (USB)` | No | **Linux only** (v1). Apple File Conduit over **usbmuxd**; DCIM-focused; system packages on `PATH` (no catalog download). |

- User selects exactly one method via a **segmented toggle** on Step 1.
- Selection is persisted for the session (v1 session-only is OK).
- Changing method while idle **re-runs device detection** for USB backends only.
- **USB extract** must not start if the chosen backend reports no device (unless user explicitly picks a mounted MTP volume — see detection).
- **Wi‑Fi extract** starts a **receive session** (token in upload URL); no device picker or source-folder checklist.

### Wi‑Fi receive session

- **Start extract** mints a cryptographically random **session token** (URL query param). Token is valid until **Stop extract** or app shutdown.
- Phone opens `GET /upload?t={token}` (mobile-first HTML). User picks **files** and optionally **folders** (where the browser supports directory upload).
- Uploads are **multipart POST** to an endpoint scoped to the active token and library root.
- Files land under `{library_root}/originals/` with relative path from browser when provided (`webkitRelativePath` / filename); sanitize path segments (no `..`, no absolute paths).
- **Transfer mode is always Copy** for Wi‑Fi; **Move** is disabled in UI and rejected by API.
- **Pause:** finish in-flight upload, then reject new uploads with a clear message on the phone page until **Resume**.
- **Stop:** finish in-flight upload, invalidate token, end session.
- **Progress:** count each completed upload (and size-match skip) toward extract progress over WebSocket (same Step 1 UX as USB).
- **Platforms:** Android and iPhone browsers in scope for Wi‑Fi only; folder picker is best-effort (required on Android Chrome; optional on iOS).
- **Security:** uploads require valid session token; no open LAN ingest without an active extract session.

### Platform tooling (adapters)

**MTP (users vs app):** On Windows and Linux, MTP is already “native” for humans (Explorer, Nautilus/Dolphin, etc.). Users only need **File transfer / MTP** on the phone. They do **not** need to install libmtp manually on those OSes for normal use.

**MTP (app):** SpaceMaker needs a programmatic MTP client. Use **libmtp** (same stack on **Windows, Linux, and macOS**) in `MtpDeviceRepository` — CLI tools (`mtp-detect`, `mtp-getfile`, …) or a thin binding. Release builds **download** libmtp tools when a portable catalog entry exists; otherwise the user installs libmtp via their package manager and SpaceMaker uses `PATH`.

| OS | MTP (SpaceMaker adapter) | ADB adapter |
|----|--------------------------|-------------|
| **All** | **libmtp** (one code path), managed download or `PATH` | [adbutils](https://github.com/openatx/adbutils) + managed or `PATH` `adb` |

- **Portable app:** Download pinned `adb` (and libmtp tools when catalog provides them) into the user data folder — see [packaging/SPEC.md](../packaging/SPEC.md). Fall back to `PATH` when download fails.
- **Dev:** app downloads into managed tools dir; optional `SPACEMAKER_TOOLS_DIR` or `SPACEMAKER_DEV=1` for PATH fallback.
- **Not** primary v1: Windows WPD COM-only adapter, macOS gphoto2-only path (optional fallback later if libmtp fails on a device).
- **Domain/application** depend only on `DeviceRepository` — never import adbutils or libmtp directly.
- Adapter resolves tool path via bootstrap (managed dir → download → `PATH`); missing tools surface in the Components screen and per-feature errors.
- Unit tests use fakes; integration tests mock subprocess/adbutils.

### Info button (help content)

An **info** control (ⓘ) beside the connection method opens a panel or modal with:

1. **Wi‑Fi:** PC and phone on the **same Wi‑Fi**; click **Start extract**; scan QR or open URL; pick files/folders on the phone. Allow firewall for the app port if prompted. Move is not available.
2. **MTP:** plug phone → unlock → choose **File transfer / MTP** (not “charge only”). If libmtp was not downloaded, install it via your OS package manager when the app asks.
3. **ADB (cable):** Developer options → USB debugging → accept RSA prompt on phone. SpaceMaker downloads `adb` when possible; otherwise install platform-tools and ensure `adb` is on `PATH`.
4. **iPhone (USB):** **Linux only.** Install `usbmuxd`, `libimobiledevice`, and `ifuse`. On Arch/CachyOS, **plug in** the iPhone to start `usbmuxd` via udev (the unit has no `systemctl enable`). Unlock, tap **Trust**, keep unlocked during extract. **Camera (DCIM)** is the useful folder; iCloud-optimized photos may be absent on device.

Copy is concise; link to future docs page optional.

### iPhone USB tooling (AFC adapter)

- **Protocol:** Apple File Conduit (AFC) via **usbmuxd** — not MTP, not ADB.
- **Adapter:** `AfcDeviceRepository` — `idevice_id`, `ideviceinfo`, `idevicepair` (trust), `ifuse` mount, then directory walk + copy (same pattern as GVFS MTP).
- **Delivery:** Like **libmtp** — no portable catalog download; resolve `idevice_id`, `idevicepair`, `ideviceinfo`, and `ifuse` from managed dir (if present) then **`PATH`**. User installs distro packages when missing.
- **Platform:** **Linux only** for v1. On Windows/macOS, device API returns **501** with a clear message; UI shows setup unavailable.
- **Daemon:** If `/run/usbmuxd` (or `/var/run/usbmuxd`) is missing, surface **usbmuxd not running** with hint to plug in the iPhone (udev) or `systemctl start usbmuxd` — not `enable`, and not a failed download.
- **Move:** Delete on device via mounted path when supported; same per-file failure rules as MTP.

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

- **Start (USB):** User selects library root, **MTP, ADB, or iPhone (USB)**, **source folders**, Copy or Move mode, connected device, clicks **Start extract**.
- **Start (Wi‑Fi, Advanced):** User selects library root, **Wi‑Fi**, clicks **Start extract** — receive session opens (QR/URL).
- **Start (Wi‑Fi, Easy):** [easy-mode](../easy-mode/SPEC.md) — receive session starts automatically when Easy loads (default library root; no Start button).
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

### Scenario: Default connection method is Wi‑Fi

- **Given** the user opens Step 1 for the first time in a session
- **When** the extract form is shown
- **Then** **Wi‑Fi** is selected
- **And** **MTP** and **ADB (cable)** are available as alternates

### Scenario: Wi‑Fi upload saves to originals

- **Given** a Wi‑Fi receive session is **running** with valid token
- **When** the phone uploads a media file
- **Then** the file appears under `originals/` with expected relative path
- **And** the file is not deleted from the phone by SpaceMaker

### Scenario: Wi‑Fi rejects Move mode

- **Given** **Wi‑Fi** is selected
- **When** settings or extract start request includes **Move**
- **Then** the server forces **Copy** or returns validation error (implementation: force Copy in session)

### Scenario: Wi‑Fi pause rejects new uploads

- **Given** a Wi‑Fi receive session is **paused**
- **When** the phone attempts a new upload
- **Then** the upload is rejected with a paused message
- **And** uploads already in flight may complete

### Scenario: Wi‑Fi stop invalidates token

- **Given** a Wi‑Fi receive session was **stopped**
- **When** the phone uses the previous upload URL
- **Then** the upload page or API indicates the session has ended

### Scenario: Wi‑Fi skip duplicate by size

- **Given** a file already exists in `originals/` with the same relative path and size
- **When** the phone uploads the same file again during a session
- **Then** the upload is skipped (counted as completed)

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

### Scenario: iPhone detected via AFC (Linux)

- **Given** **iPhone (USB)** is selected on Linux, `usbmuxd` is running, and a trusted iPhone is connected
- **When** extract UI loads device status
- **Then** the device name from `ideviceinfo` is shown with **Connected via iPhone USB**
- **And** **Start extract** is enabled when library root, DCIM (or other selected folders), and device are valid

### Scenario: iPhone USB unavailable on non-Linux

- **Given** the user runs SpaceMaker on Windows or macOS
- **When** the user selects **iPhone (USB)**
- **Then** device listing fails with a clear **Linux only** message
- **And** **Start extract** remains disabled

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

### Scenario: Wi‑Fi start without USB device

- **Given** **Wi‑Fi** is selected and library root is valid
- **When** the user clicks **Start extract**
- **Then** extract enters **running** receive mode without a USB device

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
- Connection method must be `wifi`, `mtp`, `adb`, or `afc` (internal enum); UI labels as above.
- USB extract uses the repository implementation matching the selected method for the whole job (no mixing backends mid-run).
- Wi‑Fi extract uses upload receive use case + `FileSystem` only (no `DeviceRepository`).
- **Wi‑Fi:** Move mode must not be applied; at least one source folder is not required.
- **Source folders:** at least one selected; enum keys stable for API (`dcim`, `pictures`, `movies` — exact names in ports/UI DTO).
- **Job control:** only one extract job active; Pause/Resume/Stop apply to the active job; Stop is idempotent if already stopped.

## Testing strategy

| Layer | Tests |
|-------|--------|
| Unit | Idempotency: existing dest size → skip |
| Unit | Copy vs Move calls correct `DeviceRepository` methods |
| Unit | Factory selects fake MTP vs fake ADB vs fake AFC repo from user choice |
| Unit | AFC: walk mounted DCIM paths, pull/delete via test mount (no real ifuse) |
| Unit | Progress callback once per terminal file state |
| Unit | Pause/stop: given running queue → pause stops after current file; stop leaves partial progress |
| Unit | Folder filter: only paths under selected roots enter queue |
| Integration | Mock libmtp/adbutils boundaries; `tmp_path` filesystem |
| Out of scope CI | Real devices, real adb on CI |

## Out of scope

- iPhone USB on **Windows/macOS** (Linux trial only)
- Bundled/downloadable usbmuxd/ifuse in AppImage (system packages only)
- Wi‑Fi ADB (follow-up)
- Cloud relay or TLS for LAN upload (plain HTTP on LAN v1)
- Per-album or arbitrary path picker (beyond the v1 folder checklist)
- Encrypting `originals/` at rest
