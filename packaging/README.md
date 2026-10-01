# Portable release builds

Third-party CLIs are **not** embedded; they are downloaded on first run into the user data folder (see [specs/packaging/SPEC.md](../specs/packaging/SPEC.md)).

Refresh the README Home screenshot: `uv run task readme-screenshot` (writes [docs/assets/readme-home.png](../docs/assets/readme-home.png)).

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Linux AppImage: `curl`, network on first build for pinned `appimagetool`
- Windows onefile / macOS DMG: PyInstaller (`uv sync --group dev`)
- macOS DMG: `iconutil`, `hdiutil`, `codesign` (Xcode CLT)

## Linux (primary): AppImage

Pruned relocatable AppDir (managed CPython + venv + PyQt6 WebEngine), packed with squashfs zstd level 19:

```bash
uv run task build-appimage
```

Outputs (gitignored under `dist/`):

| File | Role |
|------|------|
| `SpaceMaker-<version>-<arch>.AppImage` | Double-clickable release |
| `SHA256SUMS` | SHA-256 of the AppImage |

Tagged releases (`v*`) build via [`.github/workflows/appimage.yml`](../.github/workflows/appimage.yml) and attach assets to the GitHub Release.

AppDir only (no squashfs pack):

```bash
uv run task build-installer
```

→ `dist/spacemaker-linux.AppDir/`

Details: [linux-appimage/](linux-appimage/) (`build-appdir.sh`, `prune_pyqt6.sh`).

Reference sizes (x86_64, WebEngine floor): AppDir ~675 MB unpacked → AppImage ~225 MB (zstd‑19) as of v1.0.0.

## macOS (primary): DMG with SpaceMaker.app

PyInstaller onedir + `BUNDLE` (native WKWebView / pywebview `cocoa` — no Qt), then a UDZO DMG with an Applications symlink:

```bash
uv run task build-macos-dmg
```

Outputs (gitignored under `dist/`):

| File | Role |
|------|------|
| `SpaceMaker-<version>-arm64.dmg` or `…-x86_64.dmg` | Drag-to-Applications disk image |
| `SpaceMaker.app` | App bundle (also left in `dist/` for local smoke) |
| `SHA256SUMS` | SHA-256 of the DMG |

Native arch of the build machine only (not universal2). Ad-hoc codesign is applied (`codesign -s -`); Developer ID signing and notarization are out of scope for v1.

**Gatekeeper:** first open of an unsigned download may need **Right-click → Open**, or clear the quarantine flag after you trust the build (`xattr -cr /Applications/SpaceMaker.app`).

`uv run task build-installer` on Darwin runs the same DMG build.

## Windows: PyInstaller onefile

Uses WebView2 (`edgechromium`) — no Qt bundled; PyQt6/qtpy are Linux-only dependencies.

```bash
uv sync --group dev
uv run pyinstaller packaging/spacemaker.spec --noconfirm
```

Artifact: `dist/SpaceMaker.exe`. Or `uv run task build-installer` on Windows.

## Icons

Regenerate PNG icons from the master source (and `.icns` on macOS):

```bash
uv run python scripts/packaging/sync_brand_icons.py
```

Master artwork: [assets/spacemaker-icon-source.png](assets/spacemaker-icon-source.png). App icon PNG: [assets/spacemaker-icon.png](assets/spacemaker-icon.png). macOS builds also write `assets/spacemaker.icns` at build time (not committed).

## Pins

Download URLs and versions: [tool-catalog.json](tool-catalog.json).

Legal markdown is bundled from `docs/legal/`.
