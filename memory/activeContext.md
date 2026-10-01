_Last updated: 2026-10-01 (macOS DMG packaging saved on `main`)_

## Branch

`main` (primary checkout).

## Current focus

macOS DMG packaging shipped and user-confirmed working (Finder/Dock icon + app launch).

## Just changed

- Primary macOS artifact: `SpaceMaker-<version>-<arch>.dmg` with `SpaceMaker.app` (`uv run task build-macos-dmg`).
- PyInstaller darwin onedir + BUNDLE; Windows onefile unchanged; ad-hoc codesign; `.icns` at build time.

## Next steps

1. Optional later: Developer ID signing / notarization + GitHub Actions `macos-*` release job.
2. Still open: ADB Browse speed; Easy mode import review; confirm native pywebview on real Windows GUI (macOS cocoa confirmed 2026-10-01).
