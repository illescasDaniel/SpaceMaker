_Last updated: 2026-09-23_

## Branch

`main` — packaging + 1.0 metadata committed locally; push pending.

## Current focus

**Easy mode import issues (SDD)** — wireframe approved; spec draft in `specs/easy-mode/SPEC.md`; await spec approval for panels + open-folder UX on Photo backup.

## Just changed (this commit)

- **1.0.0** release metadata (`pyproject.toml`, `app_meta`, About & Legal from API)
- Linux AppImage: drop `.xz` wrap; `SHA256SUMS` for `.AppImage` only
- **Release CI** `.github/workflows/appimage.yml` — tags `v*` only → build, smoke, GitHub Release assets
- `smoke-appimage.sh` for CI/local AppImage verification

## Next steps

1. User: **spec approved** for easy-mode import issues → implement panels
2. `git push` when ready; tag **`v1.0.0`** to trigger AppImage release workflow
3. Manual LAN test: all four modules on phone

## Run

```bash
uv run task spacemaker
uv run task checks
uv run task build-appimage    # dist/SpaceMaker-<ver>-<arch>.AppImage + SHA256SUMS
uv run task build-installer   # Linux → dist/spacemaker-linux.AppDir
```
