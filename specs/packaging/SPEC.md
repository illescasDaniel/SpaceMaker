# Packaging (portable desktop executable)

## Metadata

- **Feature:** Self-contained SpaceMaker per OS + CPU; third-party CLIs **downloaded** on first run (not shipped inside the exe)
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-components`, Settings delete control
- **Related:** [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [legal/SPEC.md](../legal/SPEC.md)
- **Manifest:** [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml)
- **Catalog:** [packaging/tool-catalog.json](../../packaging/tool-catalog.json)
- **Out of scope v1:** Auto-update, code signing, traditional installers

## Goals

End users receive a **portable desktop build** per OS. It contains the Python runtime, web UI, legal markdown, and app icon. It does **not** contain adb, libmtp, ffmpeg, ffprobe, magick, or exiftool.

On **Linux**, the primary release artifact is a **pruned relocatable AppDir** packed as an AppImage (managed CPython + venv + Qt WebEngine for pywebview). PyInstaller onefile remains optional for dev or non-Linux targets.

On first launch (or when a tool is missing from the managed folder), SpaceMaker **downloads pinned builds** from upstream or PyPI wheel sources into the standard per-user data directory:

| OS | Managed tools directory |
|----|-------------------------|
| Linux | `$XDG_DATA_HOME/spacemaker/tools` or `~/.local/share/spacemaker/tools` |
| Windows | `%LOCALAPPDATA%\SpaceMaker\tools` |
| macOS | `~/Library/Application Support/SpaceMaker/tools` |

Resolution order for each tool:

1. Executable in the managed tools directory
2. Download per [packaging/tool-catalog.json](../../packaging/tool-catalog.json) for current OS/CPU
3. Binary on the user `PATH` (user is informed the download did not succeed)
4. Missing — feature that needs the tool shows a clear manual-install message

A failed download for one tool must **not** block setup for other tools.

## Third-party programs (v1)

| Tool | Role |
|------|------|
| `adb` | ADB extract |
| `mtp-detect`, `mtp-getfile` | MTP extract (libmtp) |
| `ffmpeg`, `ffprobe` | Video encode + validation |
| `magick` | AVIF encode |
| `exiftool` | Metadata copy |

When no portable catalog entry exists for a platform (common for libmtp), skip download and rely on PATH + manual-install copy.

## Target matrix (v1)

| OS | CPU architectures | Artifact |
|----|-------------------|----------|
| **Windows** | x64 | `SpaceMaker.exe` (onefile) |
| **Linux** | x64, arm64 | `SpaceMaker-<version>-<arch>.AppImage` (pruned AppDir); optional PyInstaller onefile for dev |
| **macOS** | arm64, x64 | `SpaceMaker.app` or onefile binary |

## Runtime resolution

- Module: `spacemaker.bootstrap.bundled_tools` — `BundledTool`, `resolve_tool_path()`, `managed_tools_dir()`
- `ToolRunner` and adapters receive absolute paths from bootstrap; never assume global installs without the resolution order above.
- Optional override for tests/dev: `SPACEMAKER_TOOLS_DIR` points at a directory containing tool binaries.
- Optional `SPACEMAKER_TOOLS_DIR` for tests; production uses the managed user data folder only.

## Version pinning

- Pinned URLs, PyPI wheel coordinates, and optional sha256 live in `packaging/tool-catalog.json` per OS/CPU.
- [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml) documents purpose, homepage, license summary (legal).

## Linux AppImage (release)

- Build: `packaging/linux-appimage/build-appdir.sh` → relocatable venv under `usr/`, then [`prune_pyqt6.sh`](../../packaging/linux-appimage/prune_pyqt6.sh) (drops unused Qt modules; **keeps Qt WebEngine** for pywebview).
- Bundle metadata under `usr/share/spacemaker/` (`docs/legal/`, `packaging/tool-catalog.json`, app icon).
- Pack with pinned `appimagetool`, squashfs **zstd compression level 19**; optional `.AppImage.xz` + `SHA256SUMS` in `dist/`.
- Post-prune smoke: offscreen WebEngine load + `--server-only` HTTP.

## PyInstaller (optional / Windows / macOS)

- Onefile spec embeds `docs/legal/`, app icon, and static UI when used.
- Does **not** bundle the `tools/` CLI tree.
- [packaging/README.md](../../packaging/README.md) documents matrix build commands.

## UI

- **Components screen** (`#view-components`): shown when any required tool is not yet resolved; per-tool status (downloading, ready downloaded, using system install, needs manual install); Continue and Retry.
- **Settings** (`#view-settings`): managed folder path; **Delete downloaded components** removes only the managed tools directory; next launch may re-download.

## Acceptance criteria (BDD)

### Scenario: Convert prefers managed ffmpeg over PATH

- **Given** managed `tools/ffmpeg` exists and `/usr/bin/ffmpeg` exists
- **When** convert runs
- **Then** subprocess invokes managed `ffmpeg`, not `/usr/bin/ffmpeg`

### Scenario: Download failure falls back to PATH

- **Given** managed ffmpeg absent and catalog download fails
- **And** `ffmpeg` is on PATH
- **When** convert runs
- **Then** subprocess uses PATH ffmpeg
- **And** components status shows “Using system install” for ffmpeg

### Scenario: Portable exe has no bundled CLIs

- **Given** a built onefile artifact
- **When** the payload is inspected
- **Then** adb, ffmpeg, and magick are not embedded next to the exe

### Scenario: Legal files in artifact

- **Given** any release binary
- **When** legal paths are resolved at runtime
- **Then** privacy, disclaimer, and third-party notice markdown are available

### Scenario: Delete downloaded components

- **Given** the user clicks **Delete downloaded components** in Settings
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
| Unit | `test_bundled_tools.py` — managed dir, PATH fallback |
| Unit | `test_managed_tools.py` — ensure/delete with fake installer |
| Unit | `test_third_party_manifest.py` — manifest ↔ enum |
| Unit | `test_legal_docs_present.py` — required markdown exists |
| Unit | `test_linux_appimage_packaging.py` — AppDir script contracts (no full AppImage in CI) |
| Integration | API `/api/tools/*` with mocked downloads |

## Out of scope

- Full Android SDK (platform-tools only)
- Bundling CLIs inside the executable
- Installer welcome wizards
