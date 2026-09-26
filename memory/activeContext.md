_Last updated: 2026-09-26_

## Branch

`cursor/usb-file-transfer-c861`

## Current focus

**USB file transfer** — Phases 0–4 complete on this branch (wireframe → spec →
architecture → tests → adapters + production UI). Ready for user verification
on a machine with a phone.

## Just changed

- Domain/ports/use case + `list_file_paths` on MTP/ADB/AFC
- Session/services/API: `/api/usb-transfer/*`, `transfer_folders`, module enter
- Production `index.html` + `app.js` Home tile and Transfer screen
- Unit tests for folders, domain helpers, use case, AFC listing

## Next steps

- Manual check: Home → USB file transfer → MTP/ADB device → Start transfer
- Optional: mark draft PR ready when happy
