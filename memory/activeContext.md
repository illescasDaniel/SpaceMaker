_Last updated: 2026-09-23_

## Branch

`main` — Send files share UX committed locally; push skipped per user.

## Current focus

**Easy mode import issues (SDD)** — wireframe approved; spec draft in `specs/easy-mode/SPEC.md`; await spec approval for panels + open-folder UX on Photo backup.

## Just changed (this commit)

- **Send files** — reject empty folders; top-level folders download as zip on phone; dedupe paths; cancel folder picker no longer duplicates; reuse share session token when adding items (same QR)

## Next steps

1. User: **spec approved** for easy-mode import issues → implement panels
2. `git push` when ready; tag **`v1.0.0`** to trigger AppImage release workflow
3. Manual LAN test: Send files — scan once, add folder/file, confirm phone list updates without new QR
4. Optional: `uv run task readme-screenshot` / `uv run task checks`

## Run

```bash
uv run task spacemaker
uv run task checks
```
