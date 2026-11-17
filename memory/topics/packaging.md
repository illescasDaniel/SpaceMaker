# Packaging and releases
Updated: 2026-11-17. Release artifacts per OS, managed CLI downloads, and the Components screen.

## Now
Pinned CLIs are downloaded at first run, not bundled ([managed-cli-downloads](../notes/managed-cli-downloads.md)); Linux ships an AppImage ([linux-appimage-tag-ci](../notes/linux-appimage-tag-ci.md)), macOS a DMG ([macos-dmg-primary-artifact](../notes/macos-dmg-primary-artifact.md)); items left open after the pre-1.0 review are in [pre-1-0-deliberately-left-open](../notes/pre-1-0-deliberately-left-open.md).

## How it got here
- 2026-09-22 adb and all CLIs bundled per OS/arch, replaced the same day by managed downloads ([note](../notes/managed-cli-downloads.md)).

## Notes
- [AppImage CI on Ubuntu 24.04 needs libasound2t64](../notes/appimage-ci-ubuntu-24-libasound.md) 2026-10-02: AppImage CI on Ubuntu 24.04 needs libasound2t64, and dist/ must exist before packing on a clean checkout
- [Items left open after the pre-1.0 review](../notes/pre-1-0-deliberately-left-open.md) 2026-10-02: left open after the pre-1.0 review: tool-catalog sha256 pinning, ADB list-all-roots speed, LAN delete/export auth
- [macOS primary artifact is DMG with SpaceMaker.app](../notes/macos-dmg-primary-artifact.md) 2026-10-01: DMG with SpaceMaker.app (PyInstaller onedir + BUNDLE), ad-hoc codesign only; Windows stays onefile
- [Components chip OK when all tools resolve (incl. PATH)](../notes/components-chip-ok-incl-path.md) 2026-09-30: Components chip is OK when every tool resolves, PATH included; WARNING kept in the enum but not emitted
- [Components omits AFC tools on macOS/Windows](../notes/components-omit-afc-non-linux.md) 2026-09-30: Components hides AFC tools (idevice_*, ifuse) on macOS and Windows
- [Components stepped layout + live PATH before Continue](../notes/components-stepped-layout-live-path.md) 2026-09-30: Components probes host PATH live for display; convert stays gated until Continue
- [Prepend Homebrew / host package-manager bins to PATH](../notes/prepend-package-manager-bins-to-path.md) 2026-09-30: Homebrew and ~/.local/bin prepended to PATH at start so host-installed tools resolve
- [Components: per-tool install_command (OS/distro), drop screen setup_hint](../notes/components-install-command-per-os.md) 2026-09-30: per-tool install_command by OS/distro, display-only, built in bootstrap (no new port)
- [Move `ManagedToolsService` from `application/` to `bootstrap/services/`](../notes/managed-tools-service-in-bootstrap.md) 2026-09-29: ManagedToolsService moved to bootstrap/services/; a clean port split would need Phase 2 approval
- [Windows portable build reliability batch (QR, component downloads, shutdown)](../notes/windows-portable-reliability.md) 2026-09-24: Windows portable fixes: opaque QR, component downloads, shutdown
- [README Home screenshot via offscreen WebEngine](../notes/readme-screenshot-offscreen.md) 2026-09-23: README Home screenshot rendered offscreen with Qt WebEngine; not in CI
- [Linux 1.0 release: AppDir AppImage and tag-only CI](../notes/linux-appimage-tag-ci.md) 2026-09-23: Linux 1.0: pruned AppDir AppImage, SHA256SUMS, CI on v* tags only
- [Portable release: managed CLI downloads (not bundled in exe)](../notes/managed-cli-downloads.md) 2026-09-22: pinned CLIs downloaded into user data dirs (managed, then catalog, then PATH), not bundled

## History (superseded)
- [Bundled CLIs + legal pack](../notes/bundled-clis-legal-pack.md) 2026-09-22 → superseded by managed-cli-downloads
- [Bundle adb per OS/arch](../notes/bundle-adb-per-os.md) 2026-09-22 → superseded by managed-cli-downloads
