# Legal, privacy, and third-party notice

## Metadata

- **Feature:** Transparency for downloaded/managed binaries, privacy, and liability
- **Wireframe:** [wireframes/app.html](../../wireframes/app.html) — `#view-legal` (opened from Settings)
- **Documents:** [docs/legal/](../../docs/legal/)
- **Related:** [packaging/SPEC.md](../packaging/SPEC.md), [home-modules/SPEC.md](../home-modules/SPEC.md)

## Requirements

### Third-party tools (managed download + PATH fallback)

Official SpaceMaker **portable binaries** download pinned third-party CLIs into the user data folder on first launch. Users are **not** required to install FFmpeg, ImageMagick, ExifTool, libmtp, or adb separately when downloads succeed.

When a download fails, the app may use a tool from the user `PATH` or instruct manual installation. Privacy policy and in-app copy must state that **first launch uses the network** to fetch these programs.

See [packaging/third-party-manifest.yaml](../../packaging/third-party-manifest.yaml), [packaging/tool-catalog.json](../../packaging/tool-catalog.json), and [THIRD_PARTY_TOOLS.md](../../docs/legal/THIRD_PARTY_TOOLS.md).

### Privacy policy

Ship [PRIVACY.md](../../docs/legal/PRIVACY.md) in release artifacts. It must state:

- Local-first processing (library folders on disk; Receive files under Documents)
- Optional LAN: gallery QR, Photo backup upload, Receive files, Send files (local network only; tokenized where applicable)
- Desktop **control** APIs (settings, extract/convert, share selection, etc.) are loopback-only; phones use tokenized pages or gallery QR
- First-launch download of third-party CLI tools
- v1: no analytics telemetry unless this spec is updated

### Third-party notice

Ship [THIRD_PARTY_TOOLS.md](../../docs/legal/THIRD_PARTY_TOOLS.md) with:

- Tool name, purpose, **project home page URL**, license summary
- License texts extracted from upstream archives live beside downloaded binaries when provided

### Disclaimer

Ship [DISCLAIMER.md](../../docs/legal/DISCLAIMER.md) covering:

- User responsibility for backups
- Copy/Move and conversion may delete or move files
- **No liability** for lost or corrupted media (plain language)

### Where users see this (UI)

| Surface | Content |
|---------|---------|
| **Settings → About & Legal** | Mini page (`#view-legal`); summaries + mailto contact; third-party home links. Entry is the last row on `#view-settings` ([home-modules](../home-modules/SPEC.md)). |
| **Settings → Downloaded components** | Nested `#view-settings-tools`; managed tools folder path; **Delete downloaded components**; retry downloads ([packaging](../packaging/SPEC.md)) |
| **First run** | Components setup screen when tools are not yet resolved |
| **Release artifact** | Full `docs/legal/*.md` embedded or shipped beside the binary |

No floating footer entry points in v1. No traditional installer welcome screen in v1.

Wireframe **approved** 2026-09-22 (updated for portable release model); **updated** 2026-09-27 (Settings tab entry; About & Legal last on settings menu).

## Acceptance criteria (BDD)

### Scenario: Release artifact contains legal docs

- **Given** a built portable binary for any supported OS
- **When** legal content is resolved at runtime
- **Then** `PRIVACY.md`, `DISCLAIMER.md`, and `THIRD_PARTY_TOOLS.md` are available

### Scenario: Third-party manifest matches code

- **Given** `packaging/third-party-manifest.yaml`
- **When** CI validates the manifest
- **Then** every `BundledTool` enum value has a manifest entry

### Scenario: Settings opens legal mini page

- **Given** the user is on the Settings menu
- **When** they tap **About & Legal**
- **Then** in-app page shows Privacy, Third-party tools (with project URLs), and Disclaimer

### Scenario: Back from legal page

- **Given** the user opened About & Legal from Settings
- **When** they click **← Settings**
- **Then** they return to `#view-settings`

## Testing strategy

| Test | Location |
|------|----------|
| Manifest ↔ `BundledTool` sync | `tests/unit/test_third_party_manifest.py` |
| Managed path resolver | `tests/unit/test_bundled_tools.py` |
| Legal files exist in repo | `tests/unit/test_legal_docs_present.py` |

## Out of scope

- GDPR representative / DPO (unless product adds cloud accounts)
- Translated legal text (English v1 only)
