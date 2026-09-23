# Linux AppImage (pruned AppDir)

Adapted from the [srxy](https://github.com/) offline AppImage flow: relocatable managed CPython + venv, **Qt prune**, offscreen smoke, pinned `appimagetool`, squashfs **zstd -19**.

SpaceMaker keeps **Qt WebEngine** (pywebview Qt backend); srxy’s `prune_pyside.sh` removes WebEngine — use [`prune_pyqt6.sh`](prune_pyqt6.sh) instead.

## Scripts

| Script | Purpose |
|--------|---------|
| [`build-appdir.sh`](build-appdir.sh) | AppDir under `$APPDIR` (default `build/SpaceMaker.AppDir`) |
| [`prune_pyqt6.sh`](prune_pyqt6.sh) | Drop unused PyQt6/Qt payload after `uv pip install` |
| [`smoke_webengine.py`](smoke_webengine.py) | Offscreen `QWebEngineView` load test |

Entry from repo root:

```bash
bash scripts/packaging/build_appimage.sh
# or
uv run task build-appimage
```

Runtime bundle metadata lives in `usr/share/spacemaker/` (`docs/legal`, `packaging/tool-catalog.json`, icon). `AppRun` sets `SPACEMAKER_BUNDLE_ROOT` and runs `python -m spacemaker.desktop`.
