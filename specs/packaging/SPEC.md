# Packaging (portable desktop executable)

## Metadata

- **Feature:** Self-contained SpaceMaker per OS + CPU; third-party CLIs **downloaded** on first run (not shipped inside the exe)
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-components` (stepped: package manager → bulk install → status chip → collapsible Details; Demo: macOS missing / no brew / mixed OK / all managed + Linux / Windows), Settings → Downloaded components delete control
- **Related:** [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [legal/SPEC.md](../legal/SPEC.md)
- **Manifest:** [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml)
- **Catalog:** [packaging/tool-catalog.json](../../packaging/tool-catalog.json)
- **Wireframe approved:** 2026-09-30 (chat) — Components layout + live PATH; **re-approved** 2026-09-30 — omit AFC tools from macOS/Windows Components demos; **re-approved** 2026-09-30 — OK chip when all resolve (incl. system PATH), shorter lead copy, Details collapsed when OK
- **Spec approved:** 2026-09-30 (chat) — AFC tools Linux-only on Components; **re-approved** 2026-09-30 — OK/MISSING chip (no PATH WARNING), short lead, Details collapsed when OK
- **Architecture approved:** 2026-09-30 (chat) — auto-approved with spec (`components_tools` platform filter); **re-approved** 2026-09-30 — `summarize_tool_resolutions` → OK when all resolve (no new ports)
- **Out of scope v1:** Auto-update, code signing, traditional installers

## Design decisions

| Decision | Choice |
|----------|--------|
| **Success criteria** | On Components, the user can install missing tools from the terminal while the screen stays open: status **polls ~every 3s**, PATH-detected tools turn **green** (“Using system install”) as soon as they appear on host PATH (including Homebrew dirs), and an aggregate chip shows **OK** or **MISSING** with counts (managed vs system counts stay in the summary line). **OK** when every required tool resolves (managed **or** system PATH); **MISSING** when any required tool is unresolved. System PATH alone must **not** produce a WARNING chip. Layout top→bottom: (1) package-manager install step only when the expected PM binary is not found; (2) one **bulk** install command for all still-missing tools when a formula exists; (3) status chip always; (4) **Details** collapsible with the compact per-tool table (**collapsed** when chip is OK, including mixed managed + system; **expanded** when MISSING). Lead copy is short (downloads when possible / install missing below / refreshes / Continue reloads PATH). **Continue** always dismisses (even if some tools remain missing): re-prepends host tool PATH dirs, enables PATH fallback for convert (`components_setup_complete`), then leaves to Home. Managed downloads still preferred when present. macOS does **not** use `static-ffmpeg` PyPI wheel. **Platform-scoped tool set:** AFC tools (`idevice_id`, `idevicepair`, `ideviceinfo`, `ifuse`) are **Linux-only** on Components — omitted from status rows, bulk install, per-tool hints, and chip counts on **macOS** and **Windows** (iPhone USB / AFC is Linux-only; see [extract-media](../extract-media/SPEC.md)). |
| **Failure handling** | Catalog download failure / no portable entry → tool missing/failed with status message + per-tool install hint in Details when a formula exists. Unknown Linux family → no wrong PM guessed (no PM step formula, no bulk/per-tool Linux one-liner). If PM is missing, show PM install step; bulk/per-tool formulas still listed so the user can run them after installing the PM. Retry = catalog downloads only. App **never** runs `brew` / `winget` / `apt` / `dnf` / `pacman` / `paru` / `yay`. Poll failures are silent (keep last good snapshot). Missing AFC tools on macOS/Windows are **not** surfaced (no `brew install ifuse` / no false MISSING chip). |
| **Performance & resource budget** | Status build is local: `/etc/os-release` once per snapshot, PATH/`which` probes for PM + tools (plus host-dir prepend/probe). No network for hints. UI polls `GET /api/tools/status` about every **3s** only while `#view-components` is active; stop on leave. Bulk command is one string (multi-line OK for winget). No package-manager subprocess. Platform filter for AFC tools is a cheap set membership check (no extra I/O). |
| **Trust boundary** | Install commands (PM, bulk, per-tool) are **display-only** strings from `sys.platform` + Linux distro detection + PATH probes. User runs them in their own terminal. SpaceMaker does not elevate, does not invoke PMs, and does not write outside the managed tools dir for catalog downloads. **Display** may show `resolution=path` before Continue; **convert/subprocess** PATH fallback stays gated until Continue (or `SPACEMAKER_DEV`). After Continue, PATH tools are trusted as user-installed binaries. Enum still lists AFC tools for Linux adapters; non-Linux hosts simply never probe or hint them on Components. |

## Goals

End users receive a **portable desktop build** per OS. It contains the Python runtime, web UI, legal markdown, and app icon. It does **not** contain adb, ffmpeg, ffprobe, magick, avifenc, or exiftool.

The desktop shell's pywebview backend is native per OS: **WebView2** (`edgechromium`) on Windows, **WKWebView** (`cocoa`) on macOS — no Qt on either. **Qt WebEngine** (`qt`) is Linux-only, kept there so the app pins a known Chromium version instead of depending on the host distro's `webkit2gtk`. `pyqt6`/`pyqt6-webengine`/`qtpy` are Linux-only dependencies.

On **Linux**, the primary release artifact is a **pruned relocatable AppDir** packed as an AppImage (managed CPython + venv + Qt WebEngine for pywebview). PyInstaller onefile remains optional for dev or non-Linux targets and never bundles Qt.

On first launch (or when a tool is missing from the managed folder), SpaceMaker **downloads pinned builds** from upstream into the standard per-user data directory:

| OS | Managed tools directory |
|----|-------------------------|
| Linux | `$XDG_DATA_HOME/spacemaker/tools` or `~/.local/share/spacemaker/tools` |
| Windows | `%LOCALAPPDATA%\SpaceMaker\tools` |
| macOS | `~/Library/Application Support/SpaceMaker/tools` |

Resolution order for each tool:

1. Executable in the managed tools directory
2. Download per [packaging/tool-catalog.json](../../packaging/tool-catalog.json) for current OS/CPU
3. Binary on the user `PATH` / well-known host bins (shown live on Components; used for convert only after Continue — see Trust boundary)
4. Missing — feature that needs the tool shows a clear manual-install message

A failed download for one tool must **not** block setup for other tools.

## Third-party programs (v1)

| Tool | Role |
|------|------|
| `adb` | ADB extract / USB file transfer |
| `adbfs` | USB file transfer Browse / exist-probe mount (PATH only — e.g. `adbfs-rootless-git`; not catalog-downloaded) |
| `idevice_id`, `idevicepair`, `ideviceinfo`, `ifuse` | iPhone USB extract + USB file transfer Browse (AFC; **Linux only** — `PATH` packages **usbmuxd**, **libimobiledevice**, **ifuse**). **Not** tracked on Components for macOS/Windows. |
| `ffmpeg`, `ffprobe` | Video encode + validation |
| `magick` | Image auto-orient, thumbs, friendly JPEG, AVIF identify / non-progressive AVIF fallback |
| `avifenc` | Progressive (layered) library image → AVIF encode ([convert-media](../convert-media/SPEC.md)) |
| `exiftool` | Metadata copy |

When no portable catalog entry exists for a platform, skip download and rely on PATH + manual-install copy (with OS install hints when known). **MTP / libmtp tools are not part of SpaceMaker** (removed 2026-09-27).

**Install-hint rule:** SpaceMaker ships **no** third-party CLIs inside the executable. Missing tools get: (a) a **bulk** install command on Components when formulas exist, and (b) the same formula under that tool in **Details**. Ready managed/PATH tools omit per-tool hints. Unknown Linux family → status only (no one-liner).

**Platform-scoped Components tools:** status rows, chip counts, bulk install, and per-tool hints include only tools relevant to that OS. AFC tools (`idevice_*`, `ifuse`) appear on **Linux** only. macOS/Windows Components never list them and never emit Homebrew/winget formulas for them.

**macOS catalog:** keep portable downloads that work (`adb`, `avifenc`). Do **not** catalog `ffmpeg`/`ffprobe` via `static_ffmpeg_wheel`. Missing ffmpeg/magick/exiftool (and failed adb/avifenc downloads) use Homebrew hints.

## Target matrix (v1)

| OS | CPU architectures | Artifact |
|----|-------------------|----------|
| **Windows** | x64 | `SpaceMaker.exe` (onefile) |
| **Linux** | x64, arm64 | `SpaceMaker-<version>-<arch>.AppImage` (pruned AppDir); optional PyInstaller onefile for dev |
| **macOS** | arm64, x64 | `SpaceMaker-<version>-<arch>.dmg` (contains `SpaceMaker.app`); optional PyInstaller onefile for dev |

## Runtime resolution

- Module: `spacemaker.bootstrap.bundled_tools` — `BundledTool`, `resolve_tool_path()`, `managed_tools_dir()`, `ensure_host_tool_path_dirs()`
- `ToolRunner` and adapters receive absolute paths from bootstrap; never assume global installs without the resolution order above.
- Optional `SPACEMAKER_TOOLS_DIR` for tests; production uses the managed user data folder only.
- **Host PATH gaps (GUI launches):** at process start (and again on **Continue**), SpaceMaker prepends existing well-known package-manager bin dirs — macOS Homebrew (`/opt/homebrew/bin`, `/usr/local/bin` and matching `sbin`), Linux `~/.local/bin`. `resolve_tool_path` also probes those dirs when `which` misses. Windows ImageMagick still uses the Program Files glob.
- **Live PATH for display:** Components status may report `resolution=path` when a host binary is found **before** Continue. Convert/subprocess still require Continue (or `SPACEMAKER_DEV`) before PATH fallback is allowed.

## Version pinning

- Pinned URLs and optional sha256 live in `packaging/tool-catalog.json` per OS/CPU.
- [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml) documents purpose, homepage, license summary (legal).

## Linux AppImage (release)

- Build: `packaging/linux-appimage/build-appdir.sh` → relocatable venv under `usr/`, then [`prune_pyqt6.sh`](../../packaging/linux-appimage/prune_pyqt6.sh) (drops unused Qt modules; **keeps Qt WebEngine** for pywebview).
- Bundle metadata under `usr/share/spacemaker/` (`docs/legal/`, `packaging/tool-catalog.json`, app icon).
- Pack with pinned `appimagetool`, squashfs **zstd compression level 19**; `SHA256SUMS` in `dist/`.
- CI: GitHub Actions on version tags `v*` only (`.github/workflows/appimage.yml`).
- Post-prune smoke: offscreen WebEngine load + `--server-only` HTTP.

## macOS DMG (release)

- Build: `scripts/packaging/build_macos_dmg.sh` → PyInstaller **onedir** + `BUNDLE` → `SpaceMaker.app`, then `hdiutil` DMG.
- App icon: `packaging/assets/spacemaker.icns` generated at build time from the master PNG via `.iconset` + `iconutil`.
- Bundle id: `eu.daniel-ir.spacemaker`. Embeds `docs/legal/`, tool catalog, PNG icon, and static UI (same datas as the Windows onefile).
- Ad-hoc codesign only (`codesign --force --deep -s -`); **no** Developer ID signing or notarization (out of scope v1).
- Output: `dist/SpaceMaker-<version>-<arch>.dmg` + `SHA256SUMS` (native arch of the build machine — not universal2).
- Post-build smoke: `--help` and `--server-only` HTTP against `SpaceMaker.app/Contents/MacOS/SpaceMaker`.

## PyInstaller (Windows / optional macOS onefile)

- Windows primary artifact remains onefile `SpaceMaker.exe`.
- Spec embeds `docs/legal/`, app icon, and static UI when used.
- Does **not** bundle the `tools/` CLI tree.
- [packaging/README.md](../../packaging/README.md) documents matrix build commands.

## UI

### Components screen (`#view-components`)

Shown when setup is pending (downloads still needed and/or first-run Continue not yet chosen). Layout top → bottom (wireframe):

1. **Package manager missing** (conditional) — only when the expected PM binary is not on PATH after host-dir prepend: macOS `brew`, Windows `winget`, Linux family (`apt-get` / `dnf` / `pacman`|`paru`|`yay`). Title + short copy + `<code>` + Copy. Hidden when PM is found.
2. **Install all missing tools** (conditional) — only if ≥1 **platform-scoped** required tool is still missing **and** a combined formula can be built. One command string (dedupe packages: e.g. `ffmpeg` once for ffmpeg+ffprobe; on Linux, one `libimobiledevice` for idevice_*). Winget may be multi-line (one install per id). Hidden when nothing missing or no formulas.
3. **Tools status** (always) — chip **OK** | **MISSING** plus summary counts (e.g. `3 ready · 2 system · 1 missing`). Updates on poll and after Retry/Continue. (API may still accept a legacy `warning` value; UI treats non-`ok` / non-`missing` as non-OK for Details expand, but production never emits WARNING for PATH-only.)
4. **Details** — `<details>` with compact per-tool rows (name + status; per-tool install hint under missing/failed when a formula exists). **Collapsed** when chip is OK (including mixed managed + system PATH); **expanded** when MISSING. Managed and PATH statuses both use success green; missing/failed use error red.

**Aggregate chip rules:**

| Chip | When |
|------|------|
| **MISSING** | Any required tool not found (or still downloading / waiting) |
| **OK** | Every required tool resolves (managed **or** system PATH) |

**Live refresh:** while `#view-components` is active, poll tools status ~every **3s**; stop when leaving the screen. Retry downloads remains downloads-only (no separate Refresh control).

**Continue:** always enabled; always dismisses Components. On click: `ensure_host_tool_path_dirs()`, enable PATH fallback / write `components_setup_complete`, then navigate to Home (even if some tools are still missing).

**OS-gated chrome:** Linux shows the iPhone USB distro-packages banner; macOS and Windows hide it. Do not show brew on Windows/Linux, winget on macOS/Linux, or a mismatched Linux package manager. Do not show AFC tool rows or AFC install formulas on macOS/Windows.

**Lead copy:** short, OS-neutral — downloads when possible; install anything still missing below; status refreshes every few seconds; Continue reloads PATH.

### Settings → Downloaded components

`#view-settings-tools` (from Settings menu — [home-modules](../home-modules/SPEC.md)): managed folder path; **Delete downloaded components** removes only the managed tools directory; Retry downloads. Keep a detailed per-tool status list (same row styling as Details); full stepped Components chrome is not required here.

### Status API fields (Components)

In addition to existing `tools[]` rows (`install_command` when missing/failed):

- `summary_status`: `"ok"` | `"missing"` (legacy `"warning"` may exist in clients; server emits only `ok` / `missing` for current rules)
- `summary_line`: human counts string (or structured counts the UI formats)
- `details_expanded`: `true` when chip is MISSING (Details open by default); `false` when OK
- `package_manager_command`: `str | null` (PM step)
- `install_all_command`: `str | null` (bulk step; may contain newlines)

### Linux distro detection (backend)

Detect once when building tool status (no package-manager execution):

1. Read `/etc/os-release` `ID` and `ID_LIKE` (space-separated).
2. Map to a family:
   - **apt** — `ID` or `ID_LIKE` contains `debian` or `ubuntu` (covers Mint, Pop!, elementary, etc.)
   - **dnf** — `fedora`, `rhel`, `centos`, `rocky`, `almalinux`, or `ID_LIKE` containing `fedora` / `rhel`
   - **arch** — `arch`, `manjaro`, `endeavouros`, or `ID_LIKE` containing `arch`
3. If still unknown, probe `PATH` for `apt-get` → apt, else `dnf` → dnf, else `pacman` → arch.
4. For **arch** family only: if `paru` is on `PATH`, use `paru -S …`; else if `yay` is on `PATH`, use `yay -S …`; else `sudo pacman -S …`.
5. If still unknown → no Linux install hint (status message only).

### Package manager presence (backend)

After host-dir PATH prepend, probe:

| OS | Present if | Missing → display install (example) |
|----|------------|-------------------------------------|
| macOS | `brew` on PATH | Official Homebrew install one-liner (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`) |
| Windows | `winget` on PATH | Short copy pointing at App Installer / winget docs one-liner when known; otherwise omit PM step if no safe command |
| Linux apt | `apt-get` on PATH | Omit PM step if family is apt but `apt-get` missing is rare — if missing, status-only for PM (no wrong installer) |
| Linux dnf | `dnf` on PATH | Same |
| Linux arch | `pacman` or `paru` or `yay` | Same |

Only show the PM step when the probe fails **and** a known display command exists (macOS Homebrew install is the primary case).

### Known install formulas (display-only)

| Tool | macOS | Windows | Linux (apt) | Linux (dnf) | Linux (arch) |
|------|-------|---------|-------------|-------------|--------------|
| `ffmpeg` / `ffprobe` | `brew install ffmpeg` | `winget install -e --id Gyan.FFmpeg` | `sudo apt install ffmpeg` | `sudo dnf install ffmpeg` | `paru`/`yay`/`sudo pacman` `-S ffmpeg` |
| `magick` | `brew install imagemagick` | `winget install -e --id ImageMagick.ImageMagick` | `sudo apt install imagemagick` | `sudo dnf install ImageMagick` | `… -S imagemagick` |
| `exiftool` | `brew install exiftool` | `winget install -e --id OliverBetz.ExifTool` | `sudo apt install libimage-exiftool-perl` | `sudo dnf install perl-Image-ExifTool` | `… -S perl-image-exiftool` |
| `avifenc` | `brew install libavif` | — (no known winget id; status only if zip fails) | `sudo apt install libavif-bin` | `sudo dnf install libavif` | `… -S libavif` |
| `adb` | `brew install android-platform-tools` | `winget install -e --id Google.PlatformTools` | `sudo apt install adb` | `sudo dnf install android-tools` | `… -S android-tools` |
| `idevice_id` / `idevicepair` / `ideviceinfo` | — (AFC Linux-only; not on Components) | — | `sudo apt install libimobiledevice-utils` | `sudo dnf install libimobiledevice` | `… -S libimobiledevice` |
| `ifuse` | — (AFC Linux-only; not on Components) | — | `sudo apt install ifuse` | `sudo dnf install ifuse` | `… -S ifuse` |
| `adbfs` (PATH only; USB Browse) | — | — | — | — | `paru`/`yay` `-S adbfs-rootless-git` (AUR) |

**Bulk command:** union of packages for currently missing tools, deduped (one `ffmpeg` package for ffmpeg+ffprobe; one `libimobiledevice` for idevice_*). macOS/apt/dnf/arch: single line. Windows winget: one `winget install …` per distinct id, newline-separated.

## Acceptance criteria (BDD)

### Scenario: Convert prefers managed ffmpeg over PATH

- **Given** managed `tools/ffmpeg` exists and `/usr/bin/ffmpeg` exists
- **When** convert runs
- **Then** subprocess invokes managed `ffmpeg`, not `/usr/bin/ffmpeg`

### Scenario: Download failure falls back to PATH after Continue

- **Given** managed ffmpeg absent and catalog download fails
- **And** `ffmpeg` is on PATH
- **And** the user has chosen Continue (PATH fallback allowed)
- **When** convert runs
- **Then** subprocess uses PATH ffmpeg

### Scenario: Live PATH detection shows green before Continue

- **Given** managed ffmpeg absent
- **And** `ffmpeg` is on PATH (or under a host Homebrew bin dir)
- **And** the user has **not** chosen Continue yet
- **When** the Components status is built
- **Then** ffmpeg resolution is `path` (shown as “Using system install”, success green)
- **And** convert still does **not** use PATH ffmpeg until Continue (unless `SPACEMAKER_DEV`)

### Scenario: Aggregate chip MISSING when any tool unresolved

- **Given** at least one required tool is missing or still downloading
- **When** Components status is built
- **Then** `summary_status` is `missing`

### Scenario: Aggregate chip OK when PATH covers gaps (mixed)

- **Given** every required tool resolves
- **And** at least one resolves only via PATH (not managed)
- **When** Components status is built
- **Then** `summary_status` is `ok`
- **And** Details defaults to collapsed
- **And** bulk and PM steps are hidden

### Scenario: Aggregate chip OK when all managed

- **Given** every required tool is managed
- **When** Components status is built
- **Then** `summary_status` is `ok`
- **And** Details defaults to collapsed
- **And** bulk and PM steps are hidden

### Scenario: macOS missing brew shows package-manager step

- **Given** the app runs on macOS
- **And** `brew` is not on PATH (after host-dir prepend)
- **When** the Components screen renders
- **Then** the package-manager step is visible with the Homebrew install command
- **And** the Linux iPhone USB banner is not shown

### Scenario: macOS with brew hides package-manager step

- **Given** the app runs on macOS
- **And** `brew` is on PATH
- **When** the Components screen renders
- **Then** the package-manager step is hidden

### Scenario: Bulk install lists all missing macOS formulas

- **Given** the app runs on macOS
- **And** `ffmpeg`, `magick`, and `exiftool` are missing
- **When** the Components screen renders
- **Then** the bulk install step is visible
- **And** its command includes `brew install` with `ffmpeg`, `imagemagick`, and `exiftool` (order may vary; packages deduped)
- **And** Details under each missing tool still shows that tool’s one-liner
- **And** the bulk command does **not** include `ifuse` or `libimobiledevice`

### Scenario: macOS Components omits AFC tools

- **Given** the app runs on macOS
- **And** `ifuse`, `idevice_id`, `idevicepair`, and `ideviceinfo` are not on PATH
- **When** Components status is built
- **Then** those tools are absent from `tools[]` rows
- **And** they do not contribute to MISSING / OK chip counts
- **And** no per-tool or bulk install hint mentions `ifuse` or `libimobiledevice`

### Scenario: Windows Components omits AFC tools

- **Given** the app runs on Windows
- **And** AFC tools are not installed
- **When** Components status is built
- **Then** `idevice_id`, `idevicepair`, `ideviceinfo`, and `ifuse` are absent from `tools[]`
- **And** no winget (or other) install hint is shown for them

### Scenario: Linux Components still tracks AFC tools

- **Given** the app runs on Linux
- **And** `ifuse` is missing
- **When** Components status is built
- **Then** `ifuse` appears in `tools[]` as missing
- **And** a distro install hint is shown when the package family is known
- **And** the iPhone USB packages banner is shown

### Scenario: No missing tools hides bulk step

- **Given** no required tool is missing
- **When** the Components screen renders
- **Then** the bulk install step is hidden

### Scenario: Components polls while visible

- **Given** the Components screen is active
- **When** a few seconds elapse
- **Then** the client requests tools status again (~every 3s)
- **And** when the user leaves Components, polling stops

### Scenario: Continue re-probes PATH and dismisses

- **Given** the Components screen is shown
- **When** the user clicks Continue
- **Then** host tool PATH dirs are ensured again
- **And** PATH fallback is allowed for convert
- **And** the app leaves Components for Home even if some tools are still missing

### Scenario: macOS GUI PATH gap still finds Homebrew tools

- **Given** the app runs on macOS
- **And** process `PATH` does not include Homebrew (`/opt/homebrew/bin` or `/usr/local/bin`)
- **And** `ffmpeg` exists under that Homebrew bin dir
- **When** components status resolves ffmpeg (display probe)
- **Then** SpaceMaker finds Homebrew `ffmpeg` (via PATH prepend and/or host-dir probe)

### Scenario: Windows missing ImageMagick shows winget in Details and bulk

- **Given** the app runs on Windows
- **And** `magick` is missing
- **When** the Components screen renders
- **Then** under the magick row the install hint includes `winget install` and `ImageMagick.ImageMagick`
- **And** the bulk command includes that winget install line
- **And** no Homebrew command is shown

### Scenario: Linux apt family shows apt under failed download

- **Given** the app runs on Linux
- **And** distro detection resolves to the apt family (e.g. Ubuntu via `/etc/os-release`)
- **And** `avifenc` catalog download failed
- **When** the Components screen renders
- **Then** under the avifenc row the install hint includes `sudo apt install libavif-bin`
- **And** the bulk command includes `libavif-bin`
- **And** no `brew install` or `winget install` hint appears
- **And** the iPhone USB packages banner is shown

### Scenario: Linux dnf family shows dnf under failed tool

- **Given** the app runs on Linux
- **And** distro detection resolves to the dnf family (e.g. Fedora)
- **And** `ffmpeg` is missing or its download failed
- **When** the Components screen renders
- **Then** under the ffmpeg row the install hint includes `sudo dnf install ffmpeg`

### Scenario: Linux arch family prefers paru when present

- **Given** the app runs on Linux
- **And** distro detection resolves to the arch family
- **And** `paru` is on `PATH`
- **And** `magick` is missing
- **When** the Components screen renders
- **Then** under the magick row the install hint includes `paru -S imagemagick`

### Scenario: Linux unknown distro omits package one-liner

- **Given** the app runs on Linux
- **And** `/etc/os-release` and PATH probes do not map to apt, dnf, or arch
- **And** a catalog tool download fails
- **When** the Components screen renders
- **Then** that tool shows its failure status with no install command under the row
- **And** the bulk step is hidden (or has no Linux one-liner)
- **And** the iPhone USB packages banner is still shown

### Scenario: Failed adb download shows system install command

- **Given** the app runs on macOS
- **And** the catalog download for `adb` failed
- **When** the Components screen renders
- **Then** under the adb row the install hint includes `brew install android-platform-tools`

### Scenario: Ready managed tool omits install hint

- **Given** managed `adb` is present
- **When** the Components screen renders
- **Then** the adb row shows Ready (downloaded)
- **And** no install command appears under adb

### Scenario: macOS catalog has no static-ffmpeg wheel

- **Given** `packaging/tool-catalog.json` for `macos-aarch64` and `macos-x86_64`
- **When** the catalog is loaded
- **Then** there is no `ffmpeg` entry using strategy `static_ffmpeg_wheel`

### Scenario: Portable exe has no bundled CLIs

- **Given** a built onefile or macOS `.app` artifact
- **When** the payload is inspected
- **Then** adb, ffmpeg, and magick are not embedded next to the exe / inside the app bundle as managed CLIs

### Scenario: macOS DMG contains SpaceMaker.app with icon

- **Given** a built `SpaceMaker-<version>-<arch>.dmg`
- **When** the DMG is mounted
- **Then** it contains `SpaceMaker.app`
- **And** the app has a Finder/Dock icon (`.icns` in `Contents/Resources`)
- **And** the executable is at `Contents/MacOS/SpaceMaker`

### Scenario: Legal files in artifact

- **Given** any release binary (including frozen `_MEIPASS` inside `SpaceMaker.app`)
- **When** legal paths are resolved at runtime
- **Then** privacy, disclaimer, and third-party notice markdown are available

### Scenario: Delete downloaded components

- **Given** the user clicks **Delete downloaded components** under Settings → Downloaded components
- **When** the action completes
- **Then** the managed tools directory is removed
- **And** system PATH tools are unchanged

### Scenario: Manifest matches BundledTool enum

- **Given** CI test `test_third_party_manifest.py`
- **When** it runs
- **Then** YAML `id` entries match `BundledTool` exactly

## Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit | `test_bundled_tools.py` — managed dir, PATH fallback, host-dir prepend/probe |
| Unit | `test_managed_tools.py` — ensure/delete; live PATH display vs Continue gate; summary_status; Continue re-PATH |
| Unit | platform setup hints — PM probe; bulk + per-tool OS/distro commands; `/etc/os-release` + PATH mapping; no `static_ffmpeg_wheel` on macOS; AFC tools omitted from macOS/Windows Components status |
| Unit | `test_third_party_manifest.py` — manifest ↔ enum |
| Unit | `test_legal_docs_present.py` — required markdown exists |
| Unit | `test_linux_appimage_packaging.py` — AppDir script contracts (no full AppImage in CI) |
| Unit | `test_macos_dmg_packaging.py` — DMG script / PyInstaller BUNDLE contracts (no full DMG build in CI) |
| Unit | `test_components_ui_contract.py` — poll interval + Details expand helpers wired in `web/src` |
| Integration / UI | Components poll start/stop; stepped chrome visibility; Continue dismiss |

## Out of scope

- Full Android SDK (platform-tools only)
- Bundling CLIs inside the executable
- Installer welcome wizards
- Automatically running `brew`, `winget`, `apt`, `dnf`, `pacman`, `paru`, or `yay` from the app
- Auto-dismissing Components when the chip becomes OK (Continue still required once for first-run PATH trust)
- Copying Homebrew- or distro-installed binaries into the managed tools directory
- Exhaustive coverage of every Linux distribution (unknown → no one-liner)
