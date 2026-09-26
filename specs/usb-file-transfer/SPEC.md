# USB file transfer (phone → Documents, cable)

## Metadata

- **Feature:** Copy or move arbitrary files from a phone over USB into Documents — no conversion
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-usb-file-transfer` + Home tile `usb_file_transfer`. **Wireframe approved** 2026-09-26
- **Related:** [home-modules](../home-modules/SPEC.md), [receive-files](../receive-files/SPEC.md) (same Documents root), [extract-media](../extract-media/SPEC.md) (shared MTP / ADB / AFC device backends; different destination and file scope)
- **Use case (planned):** `TransferUsbFiles` (name may refine in Phase 2)
- **Ports (planned):** reuse outbound `DeviceRepository` adapters; destination via Documents path (not photo library `originals/`)

## Triggers & routing

- **Entry:** Home hub → **USB file transfer** → `POST /api/module/enter` with `{ "module": "usb_file_transfer" }`.
- **View:** `#view-usb-file-transfer` (single Transfer card — not the three-step USB photo backup wizard).
- **Exit:** Breadcrumb or header **Home** → `POST /api/module/home` (stops any in-flight transfer job gracefully: finish current file, then stop).
- **Not entered via:** Wi‑Fi QR, Photo backup, USB photo backup, Receive files, or Send files.

## Connection methods

| Method | UI label | Default | Platforms | Notes |
|--------|----------|---------|-----------|--------|
| **MTP** | `MTP` | **Yes** | All (tooling as in extract-media) | File transfer mode; no USB debugging. Good for Android arbitrary folders. |
| **ADB** | `ADB (cable)` | No | All | USB debugging + authorize. Prefer for Move / full folder access. |
| **AFC** | `iPhone (USB)` | No | **Linux only** (v1) | Apple File Conduit — limited exposed folders (typically Camera / DCIM). |

- Exactly one method selected via segmented toggle (same visual language as USB photo backup Extract).
- **No Wi‑Fi** in this module — use [receive-files](../receive-files/SPEC.md) for LAN uploads.
- Changing method while idle re-runs device detection for that backend.
- Transfer must not start if the chosen backend reports no usable device.

### Info panels (ⓘ)

Always-visible body copy stays minimal. Detail lives behind ⓘ toggles (collapsed by default), matching the approved wireframe:

1. **Connection** — MTP / ADB / iPhone setup (same substance as extract-media USB help; no Wi‑Fi section).
2. **Destination** — files under `~/Documents/SpaceMaker/`; same root as Receive files; nested paths preserved; no `originals/` / convert pipeline.
3. **Mode** — Copy vs Move; Move deletes on device after successful copy when supported (ADB preferred; MTP/iPhone may fall back to copy-only per file).
4. **Actions** — Pause finishes the current file then waits; Stop ends the queue after the current file; completed files stay in the destination.

### iPhone limit banner

- Shown **only** when connection method is **iPhone (USB) / AFC** (and a connected iPhone path is the active context).
- **Hidden** for MTP and ADB.
- Copy: access is limited to folders the device exposes over USB (typically Camera); full document pickers → Wi‑Fi **Receive files**.

## Source folders

Multi-select checklist. At least one folder required to enable **Start transfer**.

### Android (MTP / ADB)

| Folder (label) | Typical path (ADB) | Default |
|----------------|--------------------|---------|
| **Download** | `/sdcard/Download` | On |
| **Documents** | `/sdcard/Documents` | On |
| **Camera (DCIM)** | `/sdcard/DCIM` | Off |
| **Pictures** | `/sdcard/Pictures` | Off |
| **Movies** | `/sdcard/Movies` | Off |
| **Music** | `/sdcard/Music` | Off |

Adapters map labels to MTP volume paths equivalently. Queue includes **any file type** under selected roots (not media-only).

### iPhone (AFC)

- Checklist lists only folders the backend can expose (v1: **Camera (DCIM)** when present).
- Selecting iPhone switches the checklist to that limited set (wireframe behavior).

## Destination

- Root: `documents_directory()/SpaceMaker/` (create if missing) — **same** as [receive-files](../receive-files/SPEC.md).
- Preserve relative paths under each selected source folder; sanitize (`..`, absolute paths rejected).
- **No** photo library layout (`originals/`, `converted/`, `error/`, `invalid/`).
- **No** convert, gallery indexing, or HEIC/AVIF pipeline.
- Destination path field is shown read-only (or OS-default Documents path); changing the root is out of scope v1.

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

\* **Start** also requires: connected device, ≥1 folder selected, destination writable.

- **Pause:** finish in-flight file → `paused`; no new files until Resume.
- **Stop:** finish in-flight file → `stopped`; completed files remain; later Start skips size-matched destinations (idempotent).
- Progress: count + percent over WebSocket (or equivalent) without full page reload.
- **Open destination folder:** shown when the transfer session has completed or stopped with ≥1 file landed, **or** when `SpaceMaker/` under Documents already contains ≥1 file. Opens that folder in the OS file manager; if missing/removed, open Documents (do not recreate on open — same recovery as receive-files).

## Visual & UI rules

- Match approved wireframe: breadcrumb **`Home / USB file transfer`**; intro line; single **Transfer** card **without** a numbered step badge.
- Connection toggle + Connection ⓘ; conditional iPhone limit banner; device picker + friendly status (never raw `libmtp:0`-style ids as primary text).
- Folder checklist; Destination + ⓘ; Mode chips + ⓘ; status / progress / count; Actions ⓘ + Start / Pause|Resume / Stop; **Open destination folder** when applicable.
- Theme: system light/dark (`theme.css`).
- Demo-only wireframe controls are not production UI.

## Acceptance criteria (BDD)

### Scenario: Home opens USB file transfer

- **Given** the user is on the Home hub
- **When** they activate the **USB file transfer** tile
- **Then** `#view-usb-file-transfer` is shown with breadcrumb **Home / USB file transfer**
- **And** connection defaults to **MTP**
- **And** status is **Not started**
- **And** no convert or gallery controls are present

### Scenario: No step number badge

- **Given** the USB file transfer view is shown
- **When** the Transfer card renders
- **Then** the card title is **Transfer** without a numeric step badge

### Scenario: iPhone limit banner only for AFC

- **Given** MTP or ADB is selected
- **When** the transfer form is shown
- **Then** the iPhone limit banner is hidden
- **Given** **iPhone (USB)** is selected
- **When** the transfer form updates
- **Then** the iPhone limit banner is visible
- **And** the folder checklist reflects limited AFC folders (typically Camera only)

### Scenario: Detail copy behind info buttons

- **Given** the USB file transfer view is shown
- **When** Destination, Mode, and Actions ⓘ panels are collapsed
- **Then** the long destination / Move / Pause-Stop explanations are not shown as always-visible body hints
- **When** the user opens Destination ⓘ
- **Then** help text states files land under `~/Documents/SpaceMaker/` with no convert pipeline

### Scenario: Android folders include Download and Documents

- **Given** MTP or ADB is selected and a device is connected
- **When** the folder checklist is shown
- **Then** **Download** and **Documents** are available and checked by default
- **And** media folders (Camera, Pictures, Movies, Music) are available unchecked by default

### Scenario: Transfer any file type to Documents

- **Given** ADB is selected, Download is checked, and transfer is running
- **When** the queue includes `Download/report.pdf` and `Download/clip.mp4`
- **Then** both files appear under `{documents}/SpaceMaker/…` with preserved relative paths
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

### Scenario: Home breadcrumb stops transfer

- **Given** USB file transfer is running
- **When** the user taps **Home** in the breadcrumb
- **Then** the in-flight file is allowed to finish
- **And** the transfer job stops
- **And** the Home hub is shown

## Out of scope

- Wi‑Fi / QR receive in this module (see receive-files)
- Convert, gallery, `originals/` / `converted/` / `error/` / `invalid/`
- Custom destination picker outside the Documents/SpaceMaker root (v1)
- Free-text path browser on the device (checklist labels only)
- Network AFP (Apple Filing Protocol) — v1 uses **AFC** for iPhone USB only
- Pushing files PC → phone over USB
- Editing or previewing transferred files inside SpaceMaker
