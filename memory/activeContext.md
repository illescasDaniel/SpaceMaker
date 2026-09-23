_Last updated: 2026-09-23_

## Branch

`main`

## Current focus

**Easy mode import issues (SDD)** — wireframe approved; spec draft in `specs/easy-mode/SPEC.md`; await spec approval for panels + open-folder UX on Photo backup.

## Just changed (committed)

- **Security/docs/hygiene** — loopback desktop APIs + `/ws`; gallery session root only; path/XSS/CSP hardening; privacy + playbook/spec doc refresh; `.gitignore`; removed dead `ThumbnailPort` and unused packaging favicons

## Next steps

1. User: **spec approved** for easy-mode import panels → implement
2. Manual LAN test: loopback gates + phone gallery/upload still work
3. Tag **`v1.0.0`** when ready for AppImage release workflow

## Run

```bash
uv run task spacemaker
uv run task checks
```
