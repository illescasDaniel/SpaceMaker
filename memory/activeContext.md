_Last updated: 2026-09-23_

## Branch

`main` — README release commit + wider desktop window committed locally; push pending (user skipped push).

## Current focus

**Easy mode import issues (SDD)** — wireframe approved; spec draft in `specs/easy-mode/SPEC.md`; await spec approval for panels + open-folder UX on Photo backup.

## Just changed (this commit)

- **`bootstrap/window_geometry.py`** — default desktop size **1200×900** (4:3), min **800×600**
- **`desktop.py`** + **`capture_readme_home_screenshot.py`** — share those constants; README viewport note updated

## Next steps

1. User: **spec approved** for easy-mode import issues → implement panels
2. `git push` when ready; tag **`v1.0.0`** to trigger AppImage release workflow
3. Optional: `uv run task readme-screenshot` to refresh hero PNG at new width
4. Manual LAN test: all four modules on phone
5. Add GitHub Releases URL to README once remote is configured

## Run

```bash
uv run task spacemaker
uv run task checks
uv run task readme-screenshot   # refresh docs/assets/readme-home.png
uv run task build-appimage      # dist/SpaceMaker-<ver>-<arch>.AppImage + SHA256SUMS
```
