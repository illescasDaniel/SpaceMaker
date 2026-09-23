# Portable release builds

Third-party CLIs are **not** embedded; they are downloaded on first run into the user data folder (see [specs/packaging/SPEC.md](../specs/packaging/SPEC.md)).

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- Linux AppImage: `curl`, `xz` (optional wrap), network on first build for pinned `appimagetool`
- Windows/macOS onefile: PyInstaller (`uv sync --group dev`)

## Linux (primary): AppImage

Pruned relocatable AppDir (managed CPython + venv + PyQt6 WebEngine), packed with squashfs zstd level 19:

```bash
uv run task build-appimage
```

Outputs (gitignored under `dist/`):

| File | Role |
|------|------|
| `SpaceMaker-<version>-<arch>.AppImage` | Double-clickable release |
| `SpaceMaker-<version>-<arch>.AppImage.xz` | Smaller download (optional) |
| `SHA256SUMS` | Checksum of the `.xz` artifact |

AppDir only (no squashfs pack):

```bash
uv run task build-installer
```

→ `dist/spacemaker-linux.AppDir/`

Details: [linux-appimage/](linux-appimage/) (`build-appdir.sh`, `prune_pyqt6.sh`).

Reference sizes (x86_64, WebEngine floor): AppDir ~675 MB unpacked → AppImage ~225 MB (zstd‑19) as of v0.1.0.

## Windows / macOS: PyInstaller onefile

```bash
uv sync --group dev
uv run pyinstaller packaging/spacemaker.spec --noconfirm
```

Artifact: `dist/SpaceMaker` or `SpaceMaker.exe`.

## Icons

Regenerate PNG icons from the master source:

```bash
uv run python scripts/packaging/sync_brand_icons.py
```

Master artwork: [assets/spacemaker-icon-source.png](assets/spacemaker-icon-source.png).

## Pins

Download URLs and versions: [tool-catalog.json](tool-catalog.json).

Legal markdown is bundled from `docs/legal/`. App icon: [assets/spacemaker-icon.png](assets/spacemaker-icon.png).
