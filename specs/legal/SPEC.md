# Legal, privacy, and bundled third-party notice

## Metadata

- **Feature:** Transparency for bundled binaries, privacy, and liability
- **Documents:** [docs/legal/](../../docs/legal/)
- **Related:** [packaging/SPEC.md](../packaging/SPEC.md)

## Requirements

### Bundled tools (no manual downloads)

Official SpaceMaker **installers and portable binaries** must include all CLI dependencies required for extract and convert. Users must **not** be directed to download FFmpeg, ImageMagick, ExifTool, libmtp, or adb separately for normal use.

See [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml) and [THIRD_PARTY_TOOLS.md](../../docs/legal/THIRD_PARTY_TOOLS.md).

### Privacy policy

Ship [PRIVACY.md](../../docs/legal/PRIVACY.md) in release artifacts. It must state:

- Local-first processing (library folders on disk)
- Optional LAN gallery (local network only)
- List/reference to third-party bundled tools
- v1: no analytics telemetry unless this spec is updated

### Third-party notice

Ship [THIRD_PARTY_TOOLS.md](../../docs/legal/THIRD_PARTY_TOOLS.md) with:

- Tool name, purpose, **project home page URL**, license summary
- Pointer to full license files in `packaging/licenses/` inside the bundle

### Disclaimer

Ship [DISCLAIMER.md](../../docs/legal/DISCLAIMER.md) covering:

- User responsibility for backups
- Copy/Move and conversion may delete or move files
- **No liability** for lost or corrupted media (plain language)

### Where users see this (UI / installer)

| Surface | Content |
|---------|---------|
| **Installer welcome or pre-install** | Short summary + checkbox or “Continue” acknowledging Disclaimer |
| **Installer / About folder** | Full `PRIVACY.md`, `DISCLAIMER.md`, `THIRD_PARTY_TOOLS.md` as files |
| **In-app footer → About & Legal** | Mini page (wireframe `#view-legal`); summaries + mailto contact; third-party **home page** links; full markdown from bundle in production |
| **Installer welcome or pre-install** | Short summary + acknowledge Disclaimer |
| **First run (optional v1)** | One-time modal with links to footer legal page |

Wireframe **approved** 2026-09-22: footer link on all main views, not a top tab.

## Acceptance criteria (BDD)

### Scenario: Release artifact contains legal docs

- **Given** a built installer for any supported OS
- **When** the payload is inspected
- **Then** `PRIVACY.md`, `DISCLAIMER.md`, and `THIRD_PARTY_TOOLS.md` are present
- **And** `packaging/licenses/` or equivalent contains third-party license texts

### Scenario: Third-party manifest matches code

- **Given** `packaging/third-party-manifest.yaml`
- **When** CI validates the manifest
- **Then** every `BundledTool` enum value has a manifest entry (and vice versa for bundled CLIs)

### Scenario: Footer opens legal mini page

- **Given** the running app
- **When** the user clicks footer **About & Legal**
- **Then** in-app page shows Privacy (with contact), Third-party tools (with project URLs), Disclaimer
- **And** production build includes full bundled `docs/legal/*.md` content (or equivalent rendered HTML)

### Scenario: Back from legal page

- **Given** the user opened About & Legal from the wizard
- **When** they click **Back**
- **Then** they return to the wizard view

## Testing strategy

| Test | Location |
|------|----------|
| Manifest ↔ `BundledTool` sync | `tests/unit/test_third_party_manifest.py` |
| Bundled path resolver (frozen vs dev) | `tests/unit/test_bundled_tools.py` |
| Legal files exist in repo | `tests/unit/test_legal_docs_present.py` |

## Out of scope

- GDPR representative / DPO (unless product adds cloud accounts)
- Translated legal text (English v1 only)
