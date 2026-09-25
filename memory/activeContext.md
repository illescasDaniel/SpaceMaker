_Last updated: 2026-09-25_

## Branch

`cursor/transfer-files-5ada`

## Current focus

**Transfer files** — universal device-to-device temporary session (Phase 0 wireframe).

Decisions from user (2026-09-25):
- **1A:** Fifth Home tile alongside Receive/Send (keep all three).
- **2A:** Same display name + different content hash → auto-suffix (`report.pdf`, `report (2).pdf`).

## Just changed

- `wireframes/app.html` — Home tile **Transfer files**; desktop `#view-transfer-files` (QR + Add files/folder + shared session list).
- `wireframes/phone-transfer.html` — phone mix of upload + session download list; ephemeral copy; ended state.
- `wireframes/README.md` — maps new wireframe.

## Blockers

Waiting on explicit **wireframe approval** in chat before Phase 1 spec.

## Next steps

1. User reviews wireframes → reply “wireframe approved” (or change requests).
2. Phase 1: `specs/transfer-files/SPEC.md` (+ home-modules update for fifth tile).
3. Then architecture → tests → impl (one gate at a time).

## Run

```bash
xdg-open wireframes/app.html
xdg-open wireframes/phone-transfer.html
```
