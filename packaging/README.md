# Portable release builds

SpaceMaker ships as a **single executable** per OS/CPU. Third-party CLIs are **not** embedded; they are downloaded on first run into the user data folder (see [specs/packaging/SPEC.md](../specs/packaging/SPEC.md)).

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- PyInstaller (install when building): `uv pip install pyinstaller`

## Build (Linux x64 example)

```bash
uv sync --group dev
uv run pyinstaller packaging/spacemaker.spec --noconfirm
```

Artifact: `dist/SpaceMaker` (onefile).

## Matrix

| Platform | Notes |
|----------|--------|
| Linux x64 / arm64 | Run pyinstaller on target arch |
| Windows x64 | `pyinstaller packaging/spacemaker.spec` on Windows |
| macOS arm64 / x64 | Build on macOS; codesign is out of scope v1 |

## Pins

Download URLs and versions: [tool-catalog.json](tool-catalog.json).

Legal markdown is bundled from `docs/legal/`. App icon: [assets/spacemaker-icon.png](assets/spacemaker-icon.png).
