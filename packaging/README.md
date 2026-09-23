# Portable release builds

SpaceMaker ships as a **single executable** per OS/CPU. Third-party CLIs are **not** embedded; they are downloaded on first run into the user data folder (see [specs/packaging/SPEC.md](../specs/packaging/SPEC.md)).

## Prerequisites

- [uv](https://docs.astral.sh/uv/)

PyInstaller is a dev dependency; `uv sync --group dev` installs it.

## Build (Linux x64 example)

```bash
uv run task build-installer
```

Equivalent manual steps:

```bash
uv sync --group dev
uv run pyinstaller packaging/spacemaker.spec --noconfirm
```

Artifact: `dist/SpaceMaker` (onefile).

## Linux AppImage (x64 / arm64)

Double-clickable distribution on Linux (includes desktop entry + icon):

```bash
uv run task build-appimage
```

Output: `dist/SpaceMaker-<version>-<arch>.AppImage` (requires `curl` to fetch `appimagetool` on first build).

Regenerate PNG icons (app, favicon, static web) from the master source:

```bash
uv run python scripts/packaging/sync_brand_icons.py
```

Master artwork: [assets/spacemaker-icon-source.png](assets/spacemaker-icon-source.png) (phone + PC + tool).

## Matrix

| Platform | Notes |
|----------|--------|
| Linux x64 / arm64 | Run pyinstaller on target arch |
| Windows x64 | `pyinstaller packaging/spacemaker.spec` on Windows |
| macOS arm64 / x64 | Build on macOS; codesign is out of scope v1 |

## Pins

Download URLs and versions: [tool-catalog.json](tool-catalog.json).

Legal markdown is bundled from `docs/legal/`. App icon: [assets/spacemaker-icon.png](assets/spacemaker-icon.png).
