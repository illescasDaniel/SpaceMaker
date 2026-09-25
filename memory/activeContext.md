_Last updated: 2026-09-25_

## Branch

`cursor/transfer-files-5ada`

## Current focus

**Transfer files** — Phases 0–4 complete (wireframe/spec/architecture approved; tests + impl landed). Ready for user verification.

## Just changed

- Domain/ports/use case (Phase 2)
- Unit tests (`test_transfer_session.py`, `test_transfer_files_session.py`)
- `AppServices` transfer session + wipe on Home/shutdown
- Routes `/transfer`, `/api/transfer/*`
- Static: `transfer.html`, Home tile + `#view-transfer-files`, `app.js`
- `Sha256ContentHasher` adapter

## Next steps

- Manual smoke: enter Transfer files, scan QR, upload from phone, add from PC, download both ways, Home deletes staging
- Optionally mark draft PR ready when verified

## Run

```bash
uv run task spacemaker-server
# open Home → Transfer files
```
