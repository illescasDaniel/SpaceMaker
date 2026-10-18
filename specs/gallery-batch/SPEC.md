# Gallery batch actions (select, move to Trash, convert to JPEG / MP4)

## Metadata

- **Feature:** Multi-select in the Gallery with two batch actions: **Move to Trash** (system Trash, never a hard delete) and **Convert to JPEG / MP4** (universal formats, delivered as one `.zip`)
- **Use cases:** `TrashGalleryItems` (new), `ExportFriendlyMediaBatch` (new; reuses `ExportFriendlyMedia` per item)
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — tab “Gallery”, **Select** mode (`#btn-gallery-select`, `#gallery-selection-bar`, `#gallery-trash-confirm`, `#gallery-batch-alert`). **Wireframe approved** 2026-10-18 (chat): zip delivery, single-item **Delete** unchanged, per-month **Select** only.
- **Design decisions approved:** 2026-10-18 (chat)
- **Spec approved:** 2026-10-18 (chat; includes the CPU `libx264` fallback with confirmation, affecting [gallery](../gallery/SPEC.md), [convert-media](../convert-media/SPEC.md) and the adaptations playbook)
- **Related:** [gallery](../gallery/SPEC.md) (item page export + delete, caches, index), [network-passcode](../network-passcode/SPEC.md), [ui-motion](../ui-motion/SPEC.md); conversion policy: [Gallery export](../../docs/playbooks/SpaceMaker-adaptations.md) in `docs/playbooks/SpaceMaker-adaptations.md`

## Design decisions

### Success criteria

- **Trash:** every selected file that succeeds ends up in the operating-system Trash / Recycle Bin (restorable by the user from there). SpaceMaker never unlinks or overwrites a selected file as part of this action — there is **no hard-delete code path** in the batch feature.
- **Trash cleanup:** for each trashed file its gallery index row, `.thumbnails/` file and `.exports/` file(s) are removed (same cleanup as the single-item delete), and its tile disappears from the grid in place.
- **Convert:** each selected photo yields a JPEG and each selected video yields an H.264 + AAC MP4, using the same encode rules as the item-page **Download as JPEG / MP4** ([adaptations](../../docs/playbooks/SpaceMaker-adaptations.md), “Gallery export”). Items that are already friendly (JPEG; H.264 + AAC MP4) are passed through unchanged without re-encoding.
- **Originals untouched:** Convert never modifies, moves or deletes anything in `processed/`.
- **Delivery:** one `.zip` per batch, downloaded by the browser/webview with `Content-Disposition: attachment`. Archive entries are stored (no recompression, JPEG/MP4 are already compressed).
- **Idempotent:** re-running Convert on the same selection re-uses `.exports/` cache files (same freshness rule as single export) and produces an equivalent zip.
- Trash and Convert are independent per item: one item's outcome never changes another's.

### Failure handling

- **Trash unavailable or refused** (no Trash on the volume, permission, read-only mount, platform without Trash support): that file is **not deleted**, no fallback to hard delete. It stays in the Gallery and stays selected; the UI lists it with a short reason. Other files in the batch still proceed.
- **File already gone** (deleted/moved externally between selection and action): counted as done for Trash (index and caches cleaned like “external delete”), skipped with a note for Convert; no error page.
- **Convert item fails** (decode error, encoder error, source missing): the item is skipped, listed with a reason, stays selected for retry; the remaining items are still converted and zipped.
- **No hardware H.264 encoder, `libx264` available:** if the selection contains videos that need a re-encode (not already friendly, no up-to-date `.exports/` copy), **one** confirmation is shown **before the batch starts** (count of such videos; much slower because there is no GPU video encoding; **Continue** / **Cancel**). **Cancel** starts nothing (selection kept). **Continue** converts those videos on the CPU. Photos and pass-through items never trigger it, and it is never shown when a hardware encoder exists.
- **No H.264 encoder at all** (no hardware, no `libx264`): videos that need re-encoding are skipped with reason “MP4 not available on this computer”; photos and already-friendly videos in the same batch still convert.
- **Zero successful items:** no zip is produced and no download starts; the alert says nothing could be converted and lists reasons.
- **Cancel:** closing the alert with **Dismiss** after completion only hides it. Leaving the Gallery or reloading while a convert job runs does not stop the job server-side but its zip is discarded by the cleanup rule below; no half-written zip is ever offered.
- **Insufficient disk space** for the estimate (see budget): fail before starting with an inline message; nothing partially written.
- **Over the item limit:** request rejected (400) and the UI blocks the action with a count message; nothing is processed.
- **Network/HTTP failure** while polling or downloading: the alert shows a retryable error; the job result stays available until cleanup.

### Performance & resource budget

- **Selection limit:** at most **500 items** per batch (both actions). The UI disables the actions and shows “Select up to 500 items” beyond that; the server enforces the same cap.
- **Selection state** is a client-side set of relative paths (not the full library); it does not require loading unloaded timeline pages. Per-month **Select** selects only the tiles currently loaded for that month and respects the cap.
- **CPU fallback:** `libx264` runs one video at a time with the same export concurrency, at reduced scheduling priority (nice/below-normal) so the desktop stays usable; this is why a confirmation precedes it. Batches of CPU-encoded videos can take a long time; progress is per item.
- **Convert concurrency:** one item at a time per batch, and batches/single exports share the existing export concurrency (one ffmpeg/Magick conversion at a time) so the desktop stays responsive. Progress is per item (“Converting 3 of 12…”) plus the overall bar.
- **Trash:** one Trash operation per file, sequential; a 500-item batch completes with progress feedback and without blocking the event loop (blocking calls run off the loop).
- **Disk:** the zip is built under `{library_root}/.exports/.batch/{job_id}/` (inside the existing cache dir, skipped by scans). Before starting, require free space ≥ the sum of source sizes for items that need re-encoding plus the sizes of pass-through items (conservative upper bound); otherwise fail early.
- **Cleanup:** a batch zip is deleted after it has been downloaded, or after 24 h, or at the next app start, whichever comes first. `.exports/.batch/` is safe to delete anytime.
- **Network cost:** the zip is streamed from disk (`FileResponse`), never held in memory.

### Trust boundary

- **Untrusted input:** the list of relative paths, the batch format choice and job ids, which can come from LAN phones as well as the desktop webview.
- **Validation at the inbound adapter:** every path must pass `is_safe_gallery_relative_path` and resolve to an existing regular file **inside** `processed/` (no traversal, no symlink escape, never `originals/`, `error/`, `invalid/`, `.thumbnails/`, `.exports/`). Duplicates are collapsed; the list size is capped (500). Any invalid path rejects the whole request (403) before any action runs.
- **Auth:** same rules as the existing single-item routes: loopback is trusted; non-loopback clients go through the optional network passcode middleware. Trash from a LAN phone acts on the host’s Trash — allowed (same as single delete today) because it is recoverable on the host.
- **Zip contents:** entry names are derived server-side from the validated relative path (plus the new `.jpg`/`.mp4` extension where converted); client-supplied names are never used, entry names never contain `..` or absolute paths, and name collisions are impossible by construction (injective path-mirror, same rule as `.exports/`).
- **Job ids** are unguessable (random, ≥128 bits) and only grant download of that job’s zip; zips are never addressed by path.
- **Desktop save bridge:** the destination comes only from the native Save dialog (never from the page), and the bridge fetches only loopback URLs of the batch zip, the single friendly-export file and `/media/{path}?download=1`; any other URL is refused. Data is written to a `.part` file and renamed on success. A batch zip is deleted after its first fully served response, so a failed desktop save means running the batch again.
- **Trash access:** performed only through an outbound port by the host process on files already validated inside `processed/`; no shell string composition with user paths.

## Triggers & routing

- **Entry:** Gallery tab (desktop `index.html` and standalone phone `gallery_mobile.html`), Timeline and Calendar (day grid) views.
- **Enter select mode:** toolbar **Select** button (becomes **Done**). **Esc** or **Done**/**Cancel** exits and clears the selection.
- **Endpoints (names indicative; finalized in Phase 2):**
  - `POST /api/gallery/batch/trash` — body: list of relative paths; returns per-path results (`trashed` | `failed` + reason).
  - `POST /api/gallery/batch/convert` — body: list of relative paths; returns a job.
  - `GET /api/gallery/batch/convert/{job_id}` — status poll (HTTP, so LAN phones work like single export).
  - `GET /api/gallery/batch/convert/{job_id}/file` — the zip, only when the job is done.
  - `POST /api/gallery/batch/download` — body: list of relative paths; returns the same job shape as convert, but the zip holds the **stored files exactly as in `processed/`** (no conversion, no CPU confirm); status and file use the same `GET` endpoints above.
  - Desktop item page **Download** serves the stored file via the existing `/media/{path}?download=1`.

## Visual & UI rules

Aligned with the approved wireframe; theme/motion shared with [ui-motion](../ui-motion/SPEC.md).

- **Select button** in the toolbar next to the Timeline | Calendar toggle.
- **In select mode:** tile click **toggles selection** and never opens the item page; every tile shows a round check badge top-left; selected tiles show an accent outline and a ✓. Each month heading gets a small **Select** pill that selects/deselects all loaded tiles of that month (toggle: all selected → deselect all).
- **No global “select all”** (libraries can exceed 50,000 items).
- **Sticky bottom selection bar:** `N selected`, **Download** (primary, left of Convert), **Convert to JPEG / MP4** (secondary), **Move to Trash**, **Cancel**. Download, Convert and Move to Trash are visibly faded (reduced opacity, greyed, not-allowed cursor) and inert at 0 selected and over the limit; Cancel stays normal. The bar leaves a right gutter clear of the floating phone-help button on desktop.
- **Move to Trash confirm:** inline confirm panel (Settings-confirm pattern): “Move N items to the Trash? They disappear from the Gallery but stay in your system Trash, so you can restore them from there.” Buttons **Move to Trash** / **Keep**. No wording that implies permanent deletion.
- **After Trash:** successful tiles play the existing `.thumb-removing` removal in place (no timeline reload, scroll preserved; empty months disappear with their heading; reduced motion removes immediately). Failed items stay selected and are listed in an alert.
- **Convert alert:** one `#gallery-batch-alert` for the whole batch: running state “Converting i of N…” with a progress bar and the note “Photos → JPEG, videos → MP4. Your originals are not changed.”; done state “All N converted” with **Download .zip** and **Dismiss**; partial state “X of N converted · K skipped” plus the skipped list with reasons; skipped items stay selected. The gallery toolbar (with **Select**) is sticky so Select stays reachable while scrolling. The trash and CPU confirms are centred modal dialogs over a dimmed backdrop (Esc closes), and the alert floats in a sticky container directly above the selection bar so it is always visible. In the desktop shell **Download .zip** opens a native Save dialog and then shows a progress bar (“Saving SpaceMaker-export.zip… N%”, then “Saved” with the path); in a phone or browser the browser's own download UI is used.
- **Batch Download** shows the same floating alert (“Preparing N files…” progress → **Download .zip** → desktop Save dialog with progress, as for Convert) and never converts anything.
- **Desktop item page:** a new primary **Download** (saves the stored file as-is; desktop uses the native Save dialog + progress alert, no conversion) sits left of the secondary **Download as JPEG / MP4**; **Open** becomes secondary. The phone item page already has this button. **Delete** stays a permanent delete.
- **Mobile:** usable at ~320px; the bar wraps; hit targets for the check badge ≥ 44px tap area.

## Acceptance criteria (BDD)

### Scenario: Enter select mode and toggle tiles

- **Given** the Gallery timeline with loaded tiles
- **When** the user chooses **Select** and clicks two tiles
- **Then** the toolbar button reads **Done** and the bar shows “2 selected”
- **And** neither click navigated to an item page
- **When** the user presses **Esc**
- **Then** select mode ends and no tile is selected

### Scenario: Per-month Select

- **Given** select mode and a month with five loaded tiles, two already selected
- **When** the user chooses that month’s **Select** pill
- **Then** all five are selected
- **When** the user chooses it again
- **Then** all five are deselected

### Scenario: Actions disabled with nothing selected

- **Given** select mode
- **When** 0 items are selected
- **Then** **Convert to JPEG / MP4** and **Move to Trash** are disabled

### Scenario: Selection over the limit

- **Given** select mode
- **When** the selection would exceed 500 items
- **Then** the UI blocks the actions with a “Select up to 500 items” message
- **And** a direct request with more than 500 paths is rejected with 400 and nothing is processed

### Scenario: Move to Trash

- **Given** three selected items in `processed/`
- **When** the user chooses **Move to Trash** and confirms
- **Then** each file is moved to the system Trash and no longer exists in `processed/`
- **And** its index row, `.thumbnails/` file and `.exports/` file(s) are removed
- **And** its tile is removed in place without reloading the timeline

### Scenario: Trash confirm can be declined

- **Given** the Move to Trash confirm is shown
- **When** the user chooses **Keep**
- **Then** no file is moved and the selection is unchanged

### Scenario: Trash never hard-deletes

- **Given** the platform Trash operation fails for one selected file
- **When** the batch runs
- **Then** that file remains untouched in `processed/` and in the Gallery, still selected, with a reason shown
- **And** the other selected files are still moved to the Trash

### Scenario: File already gone before Trash

- **Given** a selected file was deleted outside SpaceMaker after selection
- **When** the user moves the selection to the Trash
- **Then** that item is treated as done (index and caches cleaned) and does not produce an error

### Scenario: Convert mixed photos and videos

- **Given** a selection of an AVIF photo, a PNG photo and an AV1 video, and a hardware H.264 encoder available
- **When** the user chooses **Convert to JPEG / MP4**
- **Then** the photos become JPEG and the video becomes H.264 + AAC MP4 using the single-export encode rules
- **And** the alert shows progress “Converting i of N…”
- **And** on completion one `.zip` containing the three outputs is offered for download
- **And** the sources in `processed/` are unchanged

### Scenario: Already-friendly items pass through

- **Given** a selection containing a JPEG and an H.264 + AAC MP4
- **When** the user converts the selection
- **Then** no re-encode runs for them
- **And** the zip contains the stored files unchanged

### Scenario: Convert reuses export cache

- **Given** a selected item already has an up-to-date `.exports/` file
- **When** the batch converts it
- **Then** it is not re-encoded and the cached file is zipped

### Scenario: One item fails to convert

- **Given** a selection of three items where one cannot be decoded
- **When** the batch runs
- **Then** the other two are converted and zipped
- **And** the alert reads “2 of 3 converted · 1 skipped” and lists the skipped item with a reason
- **And** the skipped item stays selected

### Scenario: No hardware encoder asks once before using the CPU

- **Given** the host has no hardware H.264 encoder and `libx264` is available
- **When** the user converts a selection of two photos and two AV1 videos
- **Then** one confirmation is shown before anything starts, naming “2 videos” and warning the conversion will be much slower without GPU video encoding
- **When** the user chooses **Cancel**
- **Then** no job starts, nothing is written and the selection is unchanged
- **When** the user chooses **Continue**
- **Then** the photos become JPEG, the videos are encoded with `libx264` + AAC, and one zip is offered

### Scenario: No CPU prompt when no video needs encoding

- **Given** the host has no hardware H.264 encoder
- **When** the user converts a selection of photos and already-friendly (or already-cached) videos
- **Then** no confirmation is shown and the batch starts immediately

### Scenario: No H.264 encoder at all

- **Given** the host has neither a hardware H.264 encoder nor `libx264`
- **When** the user converts a selection of two photos and one AV1 video
- **Then** the photos are converted and zipped
- **And** the video is skipped with the reason “MP4 not available on this computer”

### Scenario: Nothing converted

- **Given** every selected item fails to convert
- **When** the batch finishes
- **Then** no zip is produced and no download starts
- **And** the alert lists the reasons

### Scenario: Insufficient disk space

- **Given** free disk space is below the estimate for the batch
- **When** the user starts Convert
- **Then** it fails before any conversion with an inline message and nothing is written

### Scenario: Zip entries are server-derived and unique

- **Given** selected items `2025/a.avif` and `2024/a.avif`
- **When** the zip is produced
- **Then** entries are named from their relative paths with `.jpg`, so neither overwrites the other
- **And** no entry name contains `..` or an absolute path

### Scenario: Path validation rejects unsafe input

- **Given** a batch request containing `../outside.jpg`, an absolute path, a path under `originals/`, or a path resolving outside `processed/`
- **When** the request is received (trash or convert)
- **Then** it is rejected with 403 before any file is touched

### Scenario: Zip is cleaned up

- **Given** a finished batch zip
- **When** it has been downloaded, or 24 hours have passed, or the app restarts
- **Then** `{library_root}/.exports/.batch/{job_id}/` is deleted

### Scenario: Desktop saves the zip to a chosen location with progress

- **Given** the desktop shell and a finished conversion with a zip
- **When** the user taps **Download .zip** and picks a destination in the native Save dialog
- **Then** the zip is streamed to that path with a visible progress bar, the alert ends with “Saved” and the path, and a failure shows the error instead
- **And** cancelling the dialog starts nothing and keeps the zip available

### Scenario: Batch Download zips the stored files unchanged

- **Given** N selected items (photos and videos, any formats)
- **When** the user taps **Download**
- **Then** one zip is built containing each stored file byte-for-byte under its server-derived entry name, nothing is converted, no CPU confirm is shown, and the alert offers **Download .zip** (desktop: Save dialog + progress)
- **And** the same limits, path validation, disk preflight, per-item skip reporting and zip cleanup as Convert apply

### Scenario: Download is disabled with nothing selected

- **Given** select mode with 0 items selected
- **When** the user looks at or taps the selection bar actions
- **Then** **Download**, **Convert to JPEG / MP4** and **Move to Trash** are visibly faded and cannot be activated; **Cancel** stays normal

### Scenario: Desktop item page Download saves the stored file

- **Given** the desktop item page of any photo or video
- **When** the user taps **Download**
- **Then** the native Save dialog opens, then the stored file is streamed to the chosen path with a progress alert ending in “Saved” + path; cancelling does nothing; no conversion happens

### Scenario: LAN phone behaves like the desktop

- **Given** the network passcode is set and a phone is signed in
- **When** the phone selects items and runs Convert or Move to Trash from `gallery_mobile.html`
- **Then** the same endpoints work under the passcode rules, and an unsigned client gets 401

### Scenario: Single-item Delete is unchanged

- **Given** the gallery item page
- **When** the user chooses **Delete**
- **Then** behavior follows [gallery](../gallery/SPEC.md) “Delete gallery item from disk” (permanent), not this feature

## Failure scenarios

| Case | Behavior |
|------|----------|
| Trash refused / unavailable for a file | File untouched, stays selected, reason listed; others continue; never hard-delete |
| Source missing at action time | Trash: treated as done and caches cleaned; Convert: skipped with note |
| Convert item fails | Skipped with reason; rest zipped; item stays selected |
| No HW H.264, `libx264` available | One confirm before start (Continue → CPU encode, Cancel → nothing starts) |
| No H.264 encoder at all | Video skipped with reason; photos still convert |
| All items fail | No zip, no download |
| Over 500 items | UI blocked; server 400 |
| Low disk space | Fail before start, inline message |
| Unsafe path | 403 for the whole request before any action |
| Unknown / expired job id | 404; UI offers to run the conversion again |

## Validation rules

- All paths pass `is_safe_gallery_relative_path` and resolve inside `processed/` as regular files; duplicates collapsed; max 500.
- Job ids are random and unguessable; zip is served only for a job in the done phase.
- Zip entry names are produced by the server from validated relative paths only.
- Trash is performed only via the outbound Trash port; no hard-delete fallback.
- The desktop save bridge accepts only loopback URLs of the batch zip, the single friendly-export file (`/api/gallery/export/{id}/file`) and `/media/{path}?download=1`; the destination always comes from the native dialog.

## Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit | `TrashGalleryItems`: success path calls the Trash port and cleans index/thumbnail/export caches; port failure leaves file and index untouched and reports a reason; missing file treated as done; never calls a delete/unlink port |
| Unit | `ExportFriendlyMediaBatch`: mixed kinds routed to JPEG/MP4; pass-through for already-friendly; per-item failure isolated; CPU-fallback confirm required exactly once and only when a video needs encoding; no encoder at all → video skipped; zero-success yields no zip; cache reuse |
| Unit | Batch request validation: limit 500, duplicates, unsafe paths rejected before any port call |
| Unit | Zip entry naming: injective, no `..`/absolute, extension rules |
| Unit | Disk-space estimate and early failure; batch zip cleanup rules (downloaded / 24 h / restart) |
| Unit | Client selection logic (web vitest): toggle, per-month select, limit gating, Esc exit, tile click does not navigate in select mode |
| Integration | `POST /api/gallery/batch/trash` and `/convert` + status + file with fixture tree in `tmp_path` and a fake Trash port; 403 on unsafe paths; 401 under passcode for unsigned clients |
| Unit | Batch download: archive entries equal the stored bytes, no converter or encoder call, disk preflight and skips as for Convert |
| Unit | Desktop download URL guard allows the batch file URL and `/media/…?download=1` on loopback only |
| Integration | `POST /api/gallery/batch/download` + status + file; 403 unsafe paths |
| Integration | Real Trash adapter against a temp Trash dir on the host platform (marked as integration) |
| Out of scope | Visual snapshot tests until UI stable |

## Out of scope

- Changing the single-item **Delete** (stays permanent) or adding Trash to it (possible follow-up)
- Global “select all”, range (shift) selection, drag-select, and selecting across unloaded pages
- Restoring from Trash inside SpaceMaker (the OS Trash owns restore)
- Writing converted copies to a user-chosen folder (zip only in v1)
- Converting to formats other than JPEG / MP4; CPU encoding for library convert (gallery export CPU fallback is in scope, with confirmation); resize/quality options
- Batch actions on `originals/`, `error/` or `invalid/` files
