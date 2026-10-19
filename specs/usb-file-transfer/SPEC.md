# USB file transfer (phone → Documents, cable)

## Metadata

- **Feature:** Copy or move arbitrary files from a phone over USB into Documents — no conversion
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-usb-file-transfer` + Home tile `usb_file_transfer`. **Wireframe approved** 2026-09-26; **updated** 2026-09-27 (exist-only presets + Browse; MTP removed); **updated** 2026-09-27 — **Add files…** / **Add folder…** + flatten Android user-storage prefixes (**wireframe approved** 2026-09-27).
- **Spec approved:** 2026-09-26; **re-approved** 2026-09-27 (presets + Browse); **re-approved** 2026-09-27 — drop MTP; ADB default; ship ADB **adbfs** + AFC **ifuse** Browse/exist-probe together; **2026-09-27** — no preset pre-selection (user opts in); **re-approved** 2026-09-27 — dual Add buttons + path flattening
- **Architecture approved:** 2026-09-26 — `TransferUsbFiles`, `TransferFolder`, `DeviceRepositoryPort.list_file_paths`; **2026-09-27** Browse / exist-probe / extras; **2026-09-27** MTP removed, ADB+AFC Browse; **2026-09-27** — `strip_android_user_storage_prefix` in destination + Browse extras (**architecture approved** with wireframe/spec)
- **Destination selector (2026-10-19):** wireframe `#view-usb-file-transfer` Destination row (input + Browse… + Use default) approved 2026-10-19; spec revision below **approved** 2026-10-19 (chat, incl. on-disk persistence).
- **Related:** [home-modules](../home-modules/SPEC.md), [receive-files](../receive-files/SPEC.md) (same Documents root), [extract-media](../extract-media/SPEC.md) (shared ADB / AFC device backends; different destination and file scope)
- **Use case:** `TransferUsbFiles` (`application/transfer_usb_files.py`)
- **Ports:** outbound `DeviceRepositoryPort` (+ `list_file_paths`, `list_extra_file_paths`, `browse_root` / exist probe); `FileSystemPort`; destination = user-chosen folder, default `documents_directory()/SpaceMaker/` (not photo library `originals/`); `UserPreferencesPort` (+ `get/set_usb_transfer_destination`)
- **Domain:** `TransferFolder`, `usb_file_transfer` helpers (`documents_transfer_destination`, Android prefix strip); session extras as flattened device-relative paths; `AppModule.USB_FILE_TRANSFER`

> **Superseded 2026-10-19:** Browse via adbfs/native dialog is replaced by the in-app picker — see [device-file-picker](../device-file-picker/SPEC.md). ADB preset exist-probe is one `list_directory` call; iPhone keeps ifuse (listing, pull) and uses the same picker. adbfs is removed; remaining historical wording below (**Browse…**) means the picker's **Add files… / Add folder…**.

## Triggers & routing

- **Entry:** Home hub → **USB file transfer** → `POST /api/module/enter` with `{ "module": "usb_file_transfer" }`.
- **View:** `#view-usb-file-transfer` (single Transfer card — not the three-step USB photo backup wizard).
- **Exit:** Breadcrumb or header **Home** → `POST /api/module/home` (stops any in-flight transfer job gracefully: finish current file, then stop; clears Browse extras; unmounts the AFC ifuse mount owned by this session).
- **Not entered via:** Wi‑Fi QR, Photo backup, USB photo backup, Receive files, or Send files.

## Connection methods

| Method | UI label | Default | Platforms | Notes |
|--------|----------|---------|-----------|--------|
| **ADB** | `ADB (cable)` | **Yes** | All | USB debugging + authorize. Prefer for Move / full folder access. Add files/folder and the preset exist-probe use `adb shell` listing (no mount). |
| **AFC** | `iPhone (USB)` | No | **Linux only** (v1) | Apple File Conduit — limited exposed folders (typically Camera / DCIM). Browse/exist-probe via **ifuse** mount. |

- Exactly one method selected via segmented toggle (same visual language as USB photo backup Extract — **no MTP**).
- **No Wi‑Fi** in this module — use [receive-files](../receive-files/SPEC.md) for LAN uploads.
- Changing method while idle re-runs device detection for that backend, re-probes existing presets, clears Browse extras, and unmounts the previous method’s session mount.
- Transfer must not start if the chosen backend reports no usable device.

### Listing backends (Browse + exist-probe) — both required this revision

| Backend | Mount | Tooling | Notes |
|---------|-------|---------|--------|
| **ADB** | None — one `adb shell` listing per directory (picker) | bundled/PATH `adb` | No FUSE mount; works on Linux, macOS and Windows. |
| **AFC** | Session-owned **ifuse** temp mount (existing adapter pattern) | `ifuse` (+ libimobiledevice) on **PATH** | Same mount used for list/pull/picker listing/exist-probe. Unmount with session cleanup as today. |

Without a connected, authorized device: **Add files…** / **Add folder…** are disabled with the hint “needs a connected, authorized device”. Preset checklist may be empty with the empty-presets hint. iPhone USB stays Linux only.

**Out of product:** MTP / GVFS / libmtp — removed from SpaceMaker entirely (UI, adapters, packaging, docs). Users who want Explorer/Dolphin-style phone browsing use the OS file manager separately; this module uses ADB or iPhone USB only.

### Info panels (ⓘ)

Always-visible body copy stays minimal. Detail lives behind ⓘ toggles (collapsed by default), matching the approved wireframe:

1. **Connection** — ADB / iPhone setup (same substance as extract-media USB help; no Wi‑Fi; no MTP).
2. **Sources** — presets appear only when they exist; **Add files…** / **Add folder…** open the system dialog at the (flattened) phone mount and add picks.
3. **Destination** — files under the destination folder (default `~/Documents/SpaceMaker/`, same root as Receive files; changeable with **Browse…**); Android user-storage prefixes stripped; remaining nested paths preserved; no `originals/` / convert pipeline.
4. **Mode** — Copy vs Move; Move deletes on device after successful copy when supported (ADB preferred; iPhone may fall back to copy-only per file).
5. **Actions** — Pause finishes the current file then waits; Stop ends the queue after the current file; completed files stay in the destination.

### iPhone limit banner

- Shown **only** when connection method is **iPhone (USB) / AFC** (and a connected iPhone path is the active context).
- **Hidden** for ADB.
- Copy: access is limited to folders the device exposes over USB (typically Camera); full document pickers → Wi‑Fi **Receive files**.

## Source folders

Two complementary sources. **Start transfer** requires a connected device, a writable destination, and **≥1 checked preset folder and/or ≥1 Add-files/Add-folder extra**.

Section label: **Sources to transfer** (presets + removable extras).

### Preset checklist (exist-only)

Multi-select checklist of common labels. The UI lists a preset **only if that folder exists** on the connected device (probed under the mount). Missing folders are **hidden**, not shown unchecked. **No preset is pre-checked** — the user opts in. If none of the common folders exist, show a short empty hint and rely on **Add files…** / **Add folder…**.

#### Android (ADB) — candidates

| Folder (label) | Typical path (ADB) | Default when present |
|----------------|--------------------|----------------------|
| **Download** | `/sdcard/Download` | On |
| **Documents** | `/sdcard/Documents` | On |
| **Camera (DCIM)** | `/sdcard/DCIM` | Off |
| **Pictures** | `/sdcard/Pictures` | Off |
| **Movies** | `/sdcard/Movies` | Off |
| **Music** | `/sdcard/Music` | Off |

Queue includes **any file type** under selected roots (not media-only).

**Exist-probe (ADB):** one `list_directory("")` call on the storage root; directory names are matched to presets.

#### iPhone (AFC)

- Candidates limited to what AFC exposes (v1: **Camera (DCIM)** when present).
- Selecting iPhone switches the candidate set to that limited set (wireframe behavior); still hide if not present.

### Add files / Add folder extras (pick-to-add)

Native dialogs cannot select files and folders in one pick, so the UI exposes two actions (same pattern as Send / Transfer files):

| Button | Dialog | Result |
|--------|--------|--------|
| **Add files…** | Multi-file open dialog at mount root | Each selected file added as a file extra |
| **Add folder…** | Folder dialog at mount root | Selected folder added as a folder extra |

- Desktop app only. Each accepted pick is **added** to the extra sources list (does not replace or uncheck presets).
- Extras show as removable rows (display name + file/folder kind + **Remove**).
- Store extras as **flattened device-relative paths** under the mount (map host path → relative; strip Android user-storage prefixes; reject picks outside the mount).
- Duplicate extras (same flattened device-relative path) are ignored (idempotent add).
- Changing connection method or leaving via **Home** clears all extras.
- `--server-only` / missing dialog bridge / no mount: both buttons disabled with desktop-app / mount hint.

### Queue union

Transfer queue = files under checked preset roots **union** all files under each extra folder **union** each extra file. Deduplicate by device path. Skip library skip-paths as today.

### Destination relative paths (flatten Android roots)

Strip these **user-storage prefixes** (case-insensitive, longest match first) from the device path before placing under `Documents/SpaceMaker/`:

| Prefix | Example device path | Destination under SpaceMaker |
|--------|---------------------|------------------------------|
| `storage/self/primary` | `/storage/self/primary/Download/a.pdf` | `Download/a.pdf` |
| `storage/emulated/0` | `/storage/emulated/0/DCIM/b.jpg` | `DCIM/b.jpg` |
| `sdcard` | `/sdcard/WhatsApp/Media/c.opus` | `WhatsApp/Media/c.opus` |

- Apply the same strip when storing Browse extras and when computing destination for preset or extra files.
- Remaining path segments after the strip are preserved (e.g. `WhatsApp/Media/…`).
- Reject `..` / absolute escapes after normalization.

## Destination

## Design decisions (destination selector)

| Decision | Choice |
|---|---|
| **Success criteria** | The user can pick any writable absolute folder on the computer as the transfer destination with the OS folder dialog (desktop app) or by typing an absolute path; the choice is remembered across app restarts; **Use default** restores `documents_directory()/SpaceMaker/`. Everything else (prefix flattening, idempotency, Move verification) is unchanged. |
| **Failure handling** | Relative or empty path → inline error under the field, **Start transfer** disabled, nothing stored. Folder missing → created at Start; cannot create or not writable → status `failed` with the reason and no file touched. Dialog unavailable (phone browser or non-desktop shell) → banner “Browse works in the desktop app. Type an absolute path.” (same copy as the photo backup library root). Destination cannot change while a transfer is running or paused (field and Browse disabled). |
| **Performance & resource budget** | One folder dialog per click; one `Path.is_dir/mkdir` check at Start; the preference is a few bytes in the existing preferences file. |
| **Trust boundary** | The destination is set only by the desktop (loopback) via `PUT /api/settings` (already desktop-only, see [lan-access](../lan-access/SPEC.md)); it must be absolute and is normalized (no NUL). Device paths still cannot escape it (`..`/absolute rejected as before). The app never deletes or overwrites existing files in the destination beyond the existing size-matched skip rule. |

### Rules

- Default root: `documents_directory()/SpaceMaker/` (create if missing) — **same** as [receive-files](../receive-files/SPEC.md), which keeps its own fixed root; the selector affects **USB file transfer only**.
- Persisted in user preferences (survives relaunch). Unlike the photo backup library root (session state), this value is stored on disk; **Use default** clears it.
- Flatten Android user-storage prefixes (see Destination relative paths); preserve remaining relative path segments; sanitize (`..`, absolute paths rejected).
- **No** photo library layout (`originals/`, `converted/`, `error/`, `invalid/`).
- **No** convert, gallery indexing, or HEIC/AVIF pipeline.
- UI: `library-row` with the path input, **Browse…** (desktop folder dialog starting at the current value) and **Use default** (visible only when the value differs from the default); ⓘ explains default, Browse and persistence.
- **Open destination folder** opens the chosen destination (falls back to Documents if it no longer exists).

## Copy vs Move

| Mode | Device after success | PC destination |
|------|----------------------|----------------|
| Copy | File remains | File present |
| Move | File removed when backend supports delete | File present |

If Move delete fails after a successful copy: keep PC file, record per-file failure (same spirit as extract-media).

## Transfer controls

| Phase | Start | Pause | Resume | Stop |
|-------|-------|-------|--------|------|
| Idle | enabled* | disabled | hidden/disabled | disabled |
| Running | disabled | enabled | hidden/disabled | enabled |
| Paused | disabled | hidden/disabled | enabled | enabled |
| Stopped / done / error | enabled* | disabled | hidden/disabled | disabled |

\* **Start** also requires: connected device, destination writable, and **≥1 checked preset and/or ≥1 Add extra**.

- **Pause:** finish in-flight file → `paused`; no new files until Resume.
- **Stop:** finish in-flight file → `stopped`; completed files remain; later Start skips size-matched destinations (idempotent).
- Progress: count + percent over WebSocket (or equivalent) without full page reload.
- **Open destination folder:** shown when the transfer session has completed or stopped with ≥1 file landed, **or** when `SpaceMaker/` under Documents already contains ≥1 file. Opens that folder in the OS file manager; if missing/removed, open Documents (do not recreate on open — same recovery as receive-files).

## Visual & UI rules

- Match approved wireframe: breadcrumb **`Home / USB file transfer`**; intro line; single **Transfer** card **without** a numbered step badge.
- Connection toggle (**ADB** + **iPhone USB** only) + Connection ⓘ; conditional iPhone limit banner; device picker + friendly status (never raw serials/`libmtp:0`-style ids as primary text).
- **Sources to transfer** + ⓘ; exist-only preset checklist; empty-presets hint when none; removable extra rows; **Add files…** and **Add folder…** (+ unavailable hint when no mount / server-only).
- Destination + ⓘ (documents flattening); Mode chips + ⓘ; status / progress / count; Actions ⓘ + Start / Pause|Resume / Stop; **Open destination folder** when applicable.
- Theme: system light/dark (`theme.css`).
- Demo-only wireframe controls are not production UI.

## Acceptance criteria (BDD)

### Scenario: Home opens USB file transfer

- **Given** the user is on the Home hub
- **When** they activate the **USB file transfer** tile
- **Then** `#view-usb-file-transfer` is shown with breadcrumb **Home / USB file transfer**
- **And** connection defaults to **ADB (cable)**
- **And** status is **Not started**
- **And** no convert or gallery controls are present
- **And** no MTP connection option is shown

### Scenario: No step number badge

- **Given** the USB file transfer view is shown
- **When** the Transfer card renders
- **Then** the card title is **Transfer** without a numeric step badge

### Scenario: iPhone limit banner only for AFC

- **Given** ADB is selected
- **When** the transfer form is shown
- **Then** the iPhone limit banner is hidden
- **Given** **iPhone (USB)** is selected
- **When** the transfer form updates
- **Then** the iPhone limit banner is visible
- **And** the folder checklist reflects limited AFC folders that exist (typically Camera only)

### Scenario: Detail copy behind info buttons

- **Given** the USB file transfer view is shown
- **When** Sources, Destination, Mode, and Actions ⓘ panels are collapsed
- **Then** the long sources / destination / Move / Pause-Stop explanations are not shown as always-visible body hints
- **When** the user opens Destination ⓘ
- **Then** help text states files land under the destination folder (default `~/Documents/SpaceMaker/`, changeable with Browse…) with Android storage prefixes stripped and no convert pipeline

### Scenario: Missing preset folders are hidden

- **Given** ADB is selected and the storage root listing has Download and Documents but not Music
- **When** the folder checklist is shown
- **Then** **Download** and **Documents** are listed (**unchecked** by default)
- **And** **Music** is not listed

### Scenario: No common folders shows empty hint

- **Given** a connected device whose root listing has none of the preset folders
- **When** the sources section renders
- **Then** the checklist is empty
- **And** a short hint tells the user to use Add files… or Add folder…
- **And** **Start transfer** stays disabled until at least one extra is added (or a preset appears and is checked)

### Scenario: Android folders include Download and Documents when present

- **Given** ADB is selected, the device is authorized, and Download and Documents exist
- **When** the folder checklist is shown
- **Then** **Download** and **Documents** are available and **unchecked**
- **And** other present media folders (Camera, Pictures, Movies, Music) are available unchecked
- **And** **Start transfer** stays disabled until the user checks a preset and/or adds an extra

### Scenario: iPhone picker lists through the ifuse mount

- **Given** iPhone (USB) is selected on Linux, the device is trusted, and ifuse succeeds
- **When** the picker or exist-probe needs a listing
- **Then** `list_directory` reads one directory under the ifuse mount
- **And** **Add files…** and **Add folder…** are enabled
- **And** exist-probe uses that same mount

### Scenario: Add folder extra

- **Given** a mounted device and the desktop app
- **When** the user chooses **Add folder…** and selects a folder under the mount (e.g. `WhatsApp/Media`)
- **Then** that folder appears as a removable extra source
- **And** preset checkboxes are unchanged
- **When** transfer runs with that extra selected
- **Then** files under that folder are included in the queue (union with checked presets)

### Scenario: Add files extra

- **Given** a mounted device and the desktop app
- **When** the user chooses **Add files…** and selects one or more files under the mount
- **Then** each file appears as a removable extra source
- **And** transfer includes those files in the queue

### Scenario: Destination strips Android user-storage prefixes

- **Given** a queued device path `/storage/emulated/0/Download/report.pdf` (or `/sdcard/Download/report.pdf`, or `/storage/self/primary/Download/report.pdf`)
- **When** the destination path is computed
- **Then** the file lands at `{documents}/SpaceMaker/Download/report.pdf`
- **And** no `storage/`, `emulated/`, `self/`, `primary/`, or `sdcard/` segment is created under SpaceMaker for that prefix

### Scenario: Browse extras strip the same prefixes

- **Given** a mount whose relative pick is `storage/self/primary/WhatsApp/Media` (full-root mount without subdir)
- **When** the pick is accepted as an extra
- **Then** the stored extra path is `WhatsApp/Media`
- **And** the UI row displays that flattened path

### Scenario: Browse rejects paths outside the mount

- **Given** a mounted device
- **When** a pick resolves outside the phone mount root
- **Then** it is not added to extras
- **And** the user gets a clear error or the pick is ignored safely

### Scenario: Add unavailable without mount

- **Given** no device is connected or authorized (or the ifuse mount failed)
- **When** the transfer form is shown
- **Then** **Add files…** and **Add folder…** are disabled
- **And** a hint says it needs a connected, authorized device

### Scenario: Remove Add extra

- **Given** an extra source is listed
- **When** the user activates **Remove** on that row
- **Then** the extra is gone
- **And** it is no longer included in a subsequent Start

### Scenario: Home clears extras and stops transfer

- **Given** USB file transfer is running with Add extras listed
- **When** the user taps **Home** in the breadcrumb
- **Then** the in-flight file is allowed to finish
- **And** the transfer job stops
- **And** Add extras are cleared
- **And** the session-owned AFC mount is unmounted
- **And** the Home hub is shown

### Scenario: Transfer any file type to Documents

- **Given** ADB is selected, Download is checked, and transfer is running
- **When** the queue includes `/sdcard/Download/report.pdf` and `/sdcard/Download/clip.mp4`
- **Then** both files appear under `{documents}/SpaceMaker/Download/…` (prefix stripped)
- **And** neither file is sent through the convert pipeline
- **And** neither file appears in the photo gallery index

### Scenario: Copy leaves files on device

- **Given** Copy mode and a successful transfer of a file
- **When** the transfer completes that file
- **Then** the file exists on the PC destination
- **And** the file remains on the phone

### Scenario: Move removes file when supported

- **Given** Move mode over ADB and delete is supported for the file
- **When** copy to destination succeeds
- **Then** the file is removed from the phone
- **And** the file remains on the PC

### Scenario: Pause and resume transfer

- **Given** transfer is **running** with multiple files pending
- **When** the user clicks **Pause**
- **Then** the in-flight file completes
- **And** transfer enters **`paused`** with no further files started
- **When** the user clicks **Resume**
- **Then** transfer continues from the next pending file

### Scenario: Stop transfer safely

- **Given** transfer is **running** or **paused**
- **When** the user clicks **Stop**
- **Then** the in-flight file completes if any
- **And** transfer enters **`stopped`**
- **And** files already in the destination are unchanged

### Scenario: Idempotent skip by size

- **Given** a destination file already exists with the same relative path and size
- **When** a new transfer queue includes that source file
- **Then** the transfer is skipped (counted as completed)

### Scenario: No device blocks start

- **Given** the selected backend reports no device
- **When** the user attempts **Start transfer**
- **Then** transfer does not start
- **And** a clear disconnected / no-device status is shown

### Scenario: iPhone USB unavailable on non-Linux

- **Given** the user runs SpaceMaker on Windows or macOS
- **When** the user selects **iPhone (USB)**
- **Then** device listing fails with a clear **Linux only** message
- **And** **Start transfer** remains disabled

### Scenario: Open destination folder

- **Given** at least one file exists under `{documents}/SpaceMaker/`
- **When** the user activates **Open destination folder**
- **Then** the OS file manager opens that folder (or Documents if SpaceMaker was removed)

### Scenario: Choose a destination with Browse

- **Given** the desktop app is on USB file transfer and no transfer is running
- **When** the user clicks **Browse…** and picks `/home/user/Backups/Phone files`
- **Then** the Destination field shows that path, **Use default** appears, and the next transfer lands under it

### Scenario: Destination is remembered

- **Given** the user chose a custom destination
- **When** the app is restarted and USB file transfer is opened
- **Then** the Destination field shows the custom path

### Scenario: Use default

- **Given** a custom destination is set
- **When** the user clicks **Use default**
- **Then** the field shows `~/Documents/SpaceMaker` (resolved), **Use default** hides, and the stored choice is cleared

### Scenario: Invalid destination

- **Given** the user types `Backups/phone` (not absolute)
- **When** the field loses focus or Start is pressed
- **Then** the inline error shows, **Start transfer** is disabled, and the previous valid destination is kept in preferences

### Scenario: Destination locked during a transfer

- **Given** a transfer is running or paused
- **When** the user looks at the Destination row
- **Then** the Destination input, **Browse…** and **Use default** are disabled

### Scenario: Browse without the desktop shell

- **Given** the page is opened in a normal browser (no folder dialog)
- **When** the user clicks **Browse…**
- **Then** a banner asks them to type an absolute path

### Scenario: Unwritable destination

- **Given** the destination cannot be created or written
- **When** the user starts a transfer
- **Then** the status is `failed` with the reason and no phone file is deleted (even in Move mode)

## Out of scope

- **MTP / GVFS / libmtp** (removed from product)
- Wi‑Fi / QR receive in this module (see receive-files)
- Convert, gallery, `originals/` / `converted/` / `error/` / `invalid/`
- Per-transfer or per-source destinations (one destination for the module)
- Changing Receive files’ destination (it stays `~/Documents/SpaceMaker/`)
- Free-text typing of device paths (Add is mount-scoped native dialog only)
- Single native dialog that selects files and folders together (OS limitation; two buttons instead)
- Replacing the preset checklist with Add-only
- In-app virtual file tree UI
- Windows/macOS phone Browse parity in v1
- Network AFP (Apple Filing Protocol) — v1 uses **AFC** for iPhone USB only
- Pushing files PC → phone over USB
- Editing or previewing transferred files inside SpaceMaker
- Stripping arbitrary deep paths beyond the listed Android user-storage prefixes
