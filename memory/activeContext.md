_Last updated: 2026-09-22_

## Branch

`main`

## Current focus

**Wi‑Fi QR extract + convert during extract** — committed locally; push skipped per user request.

## Just changed (session)

- Wi‑Fi default extract: QR upload session, phone pages, specs/docs, tests
- **Start convert** during active extract: graceful stop + wait, then convert `originals/`

## Next steps

1. Phase 4 packaging: PyInstaller + pinned binaries in `tools/`
2. Manual smoke: Wi‑Fi upload on LAN phone; convert while extract still running

## Run

```bash
uv run task dev-tools -- --from-path
uv run task spacemaker
uv run task checks
```
