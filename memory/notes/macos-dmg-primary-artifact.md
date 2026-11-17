---
name: macos-dmg-primary-artifact
description: DMG with SpaceMaker.app (PyInstaller onedir + BUNDLE), ad-hoc codesign only; Windows stays onefile
type: decision
date: 2026-10-01
status: current
supersedes:
superseded_by:
source:
---

macOS primary artifact is DMG with SpaceMaker.app.

- **Context:** Packaging SPEC already listed `SpaceMaker.app` or onefile; Linux ships AppImage. User asked for a `.dmg` with `.app` (binary + icon) for macOS distribution.
- **Decision:** (1) Primary macOS release = `SpaceMaker-<version>-<arch>.dmg` via `scripts/packaging/build_macos_dmg.sh` / `uv run task build-macos-dmg`. (2) PyInstaller on darwin: onedir `EXE` + `COLLECT` + `BUNDLE` (`eu.daniel-ir.spacemaker`, `.icns` from `iconutil`). Windows stays onefile. (3) Ad-hoc `codesign -s -` only; Developer ID / notarization / universal2 / GitHub Actions macos release stay out of scope. (4) `build_installer` on Darwin delegates to the DMG script.
- **Rationale:** Matches common macOS distribution (drag to Applications) and parallels the Linux AppImage flow; ad-hoc sign avoids the worst local Gatekeeper friction without an Apple developer account.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-01 — macOS primary artifact is DMG with SpaceMaker.app".
