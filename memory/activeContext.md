_Last updated: 2026-09-23_

## Branch

`main` — public README + screenshot tooling committed locally; push pending (user skipped push on last save).

## Current focus

**Easy mode import issues (SDD)** — wireframe approved; spec draft in `specs/easy-mode/SPEC.md`; await spec approval for panels + open-folder UX on Photo backup.

## Just changed (this commit)

- **README.md** — public release copy (features, AppImage getting started, privacy/legal, expanded development)
- **`docs/assets/readme-home.png`** — Home hub hero image
- **`scripts/packaging/capture_readme_home_screenshot.py`** + **`uv run task readme-screenshot`**
- **packaging/README.md** — cross-link to refresh README screenshot

## Next steps

1. User: **spec approved** for easy-mode import issues → implement panels
2. `git push` when ready; tag **`v1.0.0`** to trigger AppImage release workflow
3. Manual LAN test: all four modules on phone
4. Add GitHub Releases URL to README once remote is configured

## Run

```bash
uv run task spacemaker
uv run task checks
uv run task readme-screenshot   # refresh docs/assets/readme-home.png
uv run task build-appimage      # dist/SpaceMaker-<ver>-<arch>.AppImage + SHA256SUMS
```
