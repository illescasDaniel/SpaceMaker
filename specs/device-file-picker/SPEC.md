# Device file picker (in-app phone browser)

## Metadata

- **Feature:** An in-app screen that browses a USB-connected phone one directory at a time and returns picked folders/files to its caller. Replaces the adbfs FUSE mount + native OS dialog.
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-device-picker`; entry points `#btn-uft-add-files` / `#btn-uft-add-folder` in `#view-usb-file-transfer` and `#btn-wz-add-folder` / `#btn-wz-add-files` in the USB photo backup Step 1. **Wireframe approved** 2026-10-19 (iPhone uses the same picker; photo backup gets Add folder + Add files; adbfs removed).
- **Spec approved:** _pending_
- **Callers:** [usb-file-transfer](../usb-file-transfer/SPEC.md) (**Add files…** / **Add folder…**), [extract-media](../extract-media/SPEC.md) / [main-wizard](../main-wizard/SPEC.md) Step 1 for ADB and iPhone USB (**Add folder…** / **Add files…**)
- **Ports (planned):** outbound `DeviceRepositoryPort.list_directory(device_id, path) -> DeviceDirectoryPage`; domain `DeviceEntry`
- **Supersedes:** adbfs mount path in usb-file-transfer (“Mount backends”), `adbfs` in [packaging](../packaging/SPEC.md), `docs/legal/THIRD_PARTY_TOOLS.md`

## Design decisions

_Proposed — confirm or adjust at spec review._

| Decision | Answer |
|----------|--------|
| **Success criteria** | A user on Linux, macOS or Windows with an authorized Android phone can open the picker, navigate to any folder under user storage, tick several folders/files across several directories, and see them as removable sources in the calling screen — with no extra install, no FUSE, no native dialog. The same works from a phone browser in `--server-only` mode. Picks are stored as device-relative paths (user-storage prefix stripped), identical to today’s Browse extras, so the existing transfer/extract pipelines and idempotency are unchanged. iPhone (AFC) lists through the same screen. |
| **Failure handling** | Per directory, the picker shows one of: loading, empty, permission denied (e.g. `Android/data` on Android 11+), device unauthorized, device unplugged/offline, listing timed out, generic error — each with Retry or Go up where it helps. Failures never clear ticked items. A failed listing leaves the previous directory’s selection and path intact. Closing the picker (Cancel) discards picks; Add returns them. Nothing is copied by the picker. |
| **Performance & resource budget** | One `adb shell` call (or one AFC directory read) per directory opened; never recurse; sub-folders of a ticked folder are not expanded in the picker. Directory listing of ~5 000 entries returns the first page in ≤ 2 s on USB 2; the UI renders at most 500 rows at a time (“Show N more”) and filters client-side over the loaded page set. The server holds no persistent connection and keeps at most a short-lived (≤ 30 s) listing cache per `(device, path)`. Entry payload ≤ ~150 bytes/entry. Listing is cancelled (superseded) when the user navigates away. |
| **Trust boundary** | Untrusted input: the `path` sent by the web client (including LAN phone-browser clients in `--server-only` mode) and file names returned by the phone (arbitrary unicode, spaces, quotes, newlines, `$`, backticks). The inbound route validates and normalizes `path` (no `..`, no NUL, no absolute escape, must resolve under the user-storage root) before the adapter runs; the ADB adapter passes the path as a single `shlex`-quoted argument and never builds shell from phone-provided names. File names from the phone are rendered with `textContent` only. The routes are covered by the existing network-passcode gate like every other module API ([network-passcode](../network-passcode/SPEC.md)) — no new loopback-only restriction, so a passcode-authenticated phone browser can pick. The picker only lists; copying/moving remains in the transfer/extract use cases. |

## Triggers & routing

- **Open:** from a caller button; the SPA navigates to `#view-device-picker` with a caller context `{ origin, kind: "files" | "folders", method: "adb" | "afc", mediaOnly }`. Opening does not start a server-side session; each directory read is one stateless request.
- **Breadcrumb:** `Home / <origin module> / Pick folders` (or `Pick files`). The origin crumb returns to the caller without picks.
- **API (inbound, JSON):** `POST /api/device/list` with `{ method, device_id, path, cursor? }` → `{ path, entries: [{ name, is_dir, size, mtime }], next_cursor, total, error? }`. `path` is storage-relative (`""` = **Phone storage** root = `/sdcard` canonical). Pages are ≤ 500 entries, folders first then files, case-insensitive name order, hidden (dot) entries included in the data (client toggles visibility).
- **Return:** on **Add N items** the SPA hands the ticked `[{ path, is_dir }]` to the caller; the caller posts them with its existing extras endpoint (`set_usb_transfer_extra_paths` for USB file transfer; a new equivalent for extract extras).
- **Methods:** ADB (all OS). AFC (Linux, same as today): `list_directory` reads one directory under the ifuse mount owned by the session. Root for AFC is the device root (**iPhone**), typically only `DCIM`.

## Visual & UI rules (aligned with wireframe)

- Header card: **Phone storage** (or **iPhone**) title + ⓘ; friendly device status line (never raw serials); optional media-only note when `mediaOnly`.
- Path trail (clickable crumbs, root shown as **Phone storage** — reuse `strip_android_user_storage_prefix` naming, never `/sdcard`, `storage/emulated/0` or `storage/self/primary`).
- Toolbar: **↑ Up** (disabled at root), **Select this folder** (hidden for `kind: "files"`, disabled at root), name **filter**, **Show hidden** toggle (off by default; dot-entries dimmed when shown).
- List: header row Name / Size / Modified; checkbox per row; folder name is a button that opens the folder (checkbox only selects); file rows are not links; in `kind: "folders"` file rows are visible but their checkbox is disabled; in `mediaOnly` non-media files are dimmed. Size `—` for folders. Modified column hidden at ≤ 520 px.
- Pagination footer inside the list: “Showing N of M items” + **Show 500 more**; hidden when everything is shown.
- States replace the list: loading spinner, empty, no filter match, permission denied (**Go up**), unauthorized (**Retry**), unplugged (**Retry**, ticked items kept).
- Sticky footer: selected count (`aria-live`), **Cancel**, **Add N items** (disabled at 0). Selection persists across folders within one picker session.
- Hint under the list when a folder is ticked: ticked folders are added whole, sub-folders included, when the job starts.
- Theme: system light/dark (`theme.css`); no motion beyond the existing screen fade (spinner static under `prefers-reduced-motion`). Mobile width: no horizontal page scroll.
- Entry points: USB file transfer keeps **Add files…** / **Add folder…**; the unavailable hint now reads “needs a connected, authorized device”. USB photo backup Step 1 (ADB / iPhone only; hidden for Wi‑Fi) gains an extras list + **Add folder…** + **Add files…** + ⓘ under the preset checklist, with the “only photos and videos are extracted” note.

## Behaviour details

- **Selected set:** keyed by storage-relative path. Ticking a folder and one of its descendants keeps both; the caller’s `merge_extra_paths` dedupes (parent wins).
- **Select this folder** adds the current directory as a whole-folder pick and refreshes the row/ footer state.
- **Photo backup extras:** the extract job queue = preset folders ∪ extras, filtered to media extensions (same filter as `list_media_paths`); destination stays `originals/` with stable relative paths. **Start extract** is enabled when ≥ 1 preset **or** ≥ 1 extra is selected. Extras are cleared on method change, Home exit, and library-root change, like USB file transfer extras.
- **Preset exist-probe** (USB file transfer): becomes one `list_directory("")` call — a preset shows only if a top-level directory of that name is in the listing. No FUSE walk.
- **Hidden entries:** `.thumbnails`, `.nomedia`, etc. are returned but hidden by default; `SKIPPED_LIBRARY_DIR_NAMES` still apply when expanding ticked folders.
- **Android listing command:** implementation-defined (adapter picks the most robust of `toybox stat`/`find -printf`/`ls -la` with fallback for old Android), but must be NUL- or otherwise unambiguously delimited so names with spaces/newlines parse correctly, and must return size and mtime. Symlinks resolve to their target type when cheap; otherwise are listed as files.
- **Device gone mid-browse:** next list request returns `error: "unplugged"`; the UI shows the unplugged state; Retry re-runs the same directory.

## Removal (same change set, after the picker works)

- Remove adbfs: `browse_root` / `peek_browse_root` / `cleanup_orphan_mounts` ADB paths in `adb_repository.py`, `adbfs` in `platform_setup_hints.py`, `docs/legal/THIRD_PARTY_TOOLS.md`, `adbfs` rows in [packaging](../packaging/SPEC.md), the “Mount backends” section and adbfs scenarios in [usb-file-transfer](../usb-file-transfer/SPEC.md), `tests/unit/test_adb_adbfs_browse.py`.
- Remove the native-dialog Browse route/bridge (`usb_transfer.py` host-path picks, `add_usb_transfer_extras_from_host`, `device_relative_paths_from_host_picks`) once nothing else uses them. `host_path_to_device_relative` goes with them; storage-relative paths come straight from the picker.
- Keep: **ifuse** (AFC transfer/listing), `strip_android_user_storage_prefix`, `merge_extra_paths`, extras → `list_extra_file_paths` expansion (now takes picker paths).
- Record the decision in `memory/decisions.md`.

## Acceptance criteria (BDD)

### Scenario: Open from USB file transfer

- **Given** ADB is selected and an authorized phone is connected
- **When** the user activates **Add folder…**
- **Then** the picker opens at **Phone storage** with breadcrumb `Home / USB file transfer / Pick folders`
- **And** the list shows folders before files, no `/sdcard` path anywhere in the UI

### Scenario: Open from USB photo backup

- **Given** USB photo backup Step 1 with ADB or iPhone selected
- **When** the user activates **Add folder…** or **Add files…**
- **Then** the picker opens with breadcrumb `Home / USB photo backup / Pick folders|files` and the media-only note is shown
- **And** Cancel returns to Step 1 with the extras list unchanged

### Scenario: Wi‑Fi has no picker entry

- **Given** USB photo backup Step 1
- **When** Wi‑Fi is the selected connection
- **Then** no **Add folder…** / **Add files…** controls are visible

### Scenario: Navigate and multi-select across folders

- **Given** the picker is open
- **When** the user opens `DCIM`, ticks `Camera`, goes up to **Phone storage**, opens `Download`, and ticks `report.pdf`
- **Then** the footer reads “2 items selected” and the button reads **Add 2 items**
- **When** the user activates **Add 2 items**
- **Then** the caller shows `DCIM/Camera` (folder) and `Download/report.pdf` (file) as removable sources

### Scenario: Folder click opens, checkbox selects

- **Given** a folder row
- **When** the user clicks the folder name
- **Then** that folder opens and the selection is unchanged
- **When** the user ticks the row’s checkbox
- **Then** the folder is selected without opening

### Scenario: Select this folder

- **Given** the picker is inside `WhatsApp/Media` (`kind: "folders"`)
- **When** the user activates **Select this folder**
- **Then** `WhatsApp/Media` is added to the selection as a whole folder

### Scenario: Folders-only mode disables file checkboxes

- **Given** the picker was opened with `kind: "folders"`
- **When** a directory with files is listed
- **Then** file rows have disabled checkboxes and **Select this folder** is available
- **Given** it was opened with `kind: "files"`
- **When** a directory with sub-folders is listed
- **Then** **Select this folder** is hidden, folder rows can still be opened, and folder checkboxes are disabled

### Scenario: Hidden entries off by default

- **Given** a directory containing `.thumbnails` and `.nomedia`
- **Then** they are not listed
- **When** **Show hidden** is ticked
- **Then** they are listed dimmed

### Scenario: Large folder stays responsive

- **Given** `DCIM/Camera` contains 3 412 files
- **When** the user opens it
- **Then** one directory listing is requested and at most 500 rows are rendered
- **And** the footer reads “Showing 500 of 3,412 items”
- **When** the user activates **Show 500 more**
- **Then** 500 more rows render without a new device call when already loaded
- **And** no sub-folder is listed recursively

### Scenario: Filter

- **Given** a loaded directory
- **When** the user types in the filter box
- **Then** only matching names show; with no match the **No match** state appears

### Scenario: Permission denied

- **Given** the user opens `Android/data`
- **When** the phone refuses the listing
- **Then** the permission-denied state with **Go up** is shown and the selection is untouched

### Scenario: Unauthorized device

- **Given** the phone has not accepted the USB debugging prompt
- **When** the picker lists a directory
- **Then** the unauthorized state with **Retry** is shown

### Scenario: Unplugged mid-browse keeps picks

- **Given** the user has ticked items
- **When** the cable is unplugged and a directory is opened
- **Then** the unplugged state with **Retry** is shown
- **And** the footer still shows the previous count
- **When** the phone is reconnected and Retry is activated
- **Then** the directory lists normally

### Scenario: Empty folder

- **Given** an empty directory
- **When** the user opens it
- **Then** the empty state is shown (mentions hidden files when **Show hidden** is off)

### Scenario: Awkward names

- **Given** files named `résumé final (2).pdf`, `a'b.txt`, `$HOME.txt` and a name containing a newline
- **When** the directory is listed
- **Then** each appears with its exact name, rendered as text, and the Android command receives the directory path as a single quoted argument

### Scenario: Path validation

- **Given** a list request with `path` containing `..`, a NUL byte, or an absolute path outside user storage
- **When** the route handles it
- **Then** the route returns 400 and no `adb` process is started

### Scenario: Passcode gate

- **Given** a network passcode is set and a LAN client has no login
- **When** it calls `POST /api/device/list`
- **Then** it receives 401 `passcode-required` like other module APIs
- **Given** it has a valid login (`--server-only` phone browser)
- **Then** the picker works identically to the desktop

### Scenario: Preset exist-probe uses one listing

- **Given** ADB is selected and the phone root contains `Download` and `Documents` but not `Music`
- **When** USB file transfer builds its preset checklist
- **Then** exactly one root directory listing is made and only Download and Documents appear

### Scenario: Picked paths are device-relative

- **Given** a pick of `Download/a.pdf`
- **When** the transfer runs
- **Then** the file lands at `Documents/SpaceMaker/Download/a.pdf` (no `sdcard` / `storage/emulated/0` / `storage/self/primary` segment)

### Scenario: Photo backup extras extract media only

- **Given** Step 1 extras contain `WhatsApp/Media` holding photos, videos and a PDF
- **When** extract runs
- **Then** the photos and videos land in `originals/` and the PDF is skipped

### Scenario: Photo backup Start gating

- **Given** USB photo backup with no preset folder ticked and no extras
- **Then** **Start extract** is disabled
- **When** the user adds one extra via the picker
- **Then** **Start extract** is enabled

### Scenario: iPhone through the same picker

- **Given** iPhone (USB) is selected on Linux with a trusted device and the ifuse mount present
- **When** the user opens the picker
- **Then** the root is titled **iPhone**, lists the exposed top-level folders (typically `DCIM`), and one directory is read per navigation

### Scenario: Works on every OS and in server-only mode

- **Given** the app on Linux, macOS or Windows (bundled/managed `adb`), or a phone browser against `--server-only`
- **When** the user opens the picker
- **Then** it renders and lists the phone without any mount tool, native dialog or extra install

### Scenario: Extras cleared with their session

- **Given** extras were added
- **When** the user changes connection method, leaves to Home, or (photo backup) changes library root
- **Then** the extras list is cleared

### Scenario: adbfs is gone

- **Given** the packaged app and Components screen
- **When** the picker change set is implemented
- **Then** no `adbfs` tool, hint, legal row, or mount code remains

## Out of scope

- Browsing the phone’s app-private storage, root-only paths, SD-card/secondary volumes beyond what `/sdcard` exposes (v1: user storage root only).
- Thumbnails/previews of phone files; search across directories; sorting controls; drag-and-drop.
- Recursive size/count of ticked folders before start.
- Writing to the phone, rename/delete from the picker.
- Wi‑Fi connection method (it already uses the phone’s own browser upload).
- macOS/Windows iPhone (AFC remains Linux-only; see usb-file-transfer).
- Picking the destination folder (PC side).
