# Packaging (desktop binary / installer)

## Metadata

- **Feature:** Self-contained SpaceMaker per OS + CPU; **all** third-party CLIs bundled
- **Related:** [extract-media](../extract-media/SPEC.md), [convert-media](../convert-media/SPEC.md), [legal/SPEC.md](../legal/SPEC.md)
- **Manifest:** [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml)
- **Out of scope v1:** Auto-update, code signing (follow-up)

## Goals

End users must **not** go online to install dependencies. The installer or release archive includes:

1. SpaceMaker (Python runtime + app via PyInstaller or equivalent)
2. **Every CLI** listed in the third-party manifest, built for the **target OS and CPU**
3. **Legal docs** (`PRIVACY.md`, `DISCLAIMER.md`, `THIRD_PARTY_TOOLS.md`) + `packaging/licenses/` texts (see legal spec)

## Bundled third-party binaries (v1)

| Tool | Role |
|------|------|
| `adb` | ADB extract |
| `mtp-detect`, `mtp-getfile` | MTP extract (libmtp) |
| `ffmpeg`, `ffprobe` | Video encode + validation |
| `magick` | AVIF encode |
| `exiftool` | Metadata copy |

No user-facing step may say “install FFmpeg” or “download platform-tools” for packaged builds.

## Target matrix (v1)

| OS | CPU architectures | Artifact style |
|----|-------------------|----------------|
| **Windows** | x64 | Installer or zip; `tools/*.exe` |
| **Linux** | x64, arm64 | AppImage or tarball; `tools/*` |
| **macOS** | arm64, x64 | `.app`; `Contents/Resources/tools/` |

## Runtime resolution

- Module: `spacemaker.bootstrap.bundled_tools` — `BundledTool`, `resolve_tool_path()`.
- **Frozen (release):** use `bundle_root()/tools/<name>`; **missing file = error** (no PATH fallback).
- **Dev (`uv run`):** **only** `tools/<name>`; missing file = clear error + `tools/README.md`. Optional `SPACEMAKER_DEV=1` allows `PATH` fallback for contributors without a populated `tools/` tree.
- Adapters receive absolute paths from bootstrap; never assume global installs in production.

## Version pinning

- Per-tool version files under `packaging/` (e.g. `ffmpeg.version`, `platform-tools.version`).
- CI rebuilds when pins change; manifest documents homepage + license (legal docs).

## PyInstaller

- `.spec` copies `tools/` tree + `docs/legal/` + licenses into artifact.
- `packaging/README.md` (Phase 4) documents matrix build commands.

## Acceptance criteria (BDD)

### Scenario: Convert uses bundled ffmpeg

- **Given** a frozen Linux x64 build
- **When** convert runs on a sample video
- **Then** subprocess invokes bundled `tools/ffmpeg`, not `/usr/bin/ffmpeg`

### Scenario: User never prompted to download FFmpeg

- **Given** packaged app first launch
- **When** user completes extract + convert flow
- **Then** no UI directs them to external download sites for bundled tools

### Scenario: Legal files in artifact

- **Given** any release installer
- **When** payload is listed
- **Then** privacy, disclaimer, and third-party notice files are included

### Scenario: Manifest matches BundledTool enum

- **Given** CI test `test_third_party_manifest.py`
- **When** it runs
- **Then** YAML `id` entries match `BundledTool` exactly

## Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit | `test_bundled_tools.py` — resolve frozen/dev/windows |
| Unit | `test_third_party_manifest.py` — manifest ↔ enum |
| Unit | `test_legal_docs_present.py` — required markdown exists |
| Integration | Post-build smoke: each bundled binary `--version` or equivalent |
| CI | Matrix per OS/arch |

## Out of scope

- Full Android SDK (platform-tools only)
- User-managed optional codecs outside manifest
