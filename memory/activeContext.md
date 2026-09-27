_Last updated: 2026-09-27_

## Branch

`cursor/usb-file-transfer-c861`

## Current focus

**USB file transfer** — Phases 0–4 complete on this branch. Just merged
`origin/main` (Transfer files LAN + Home layout + gallery orphan cleanup).
Ready for user verification on a machine with a phone.

## Just changed

- Merged `origin/main` into this branch; resolved conflicts keeping both
  **USB file transfer** (cable) and **Transfer files** (LAN) as Home modules
- Domain/ports/use case + `list_file_paths` on MTP/ADB/AFC
- Session/services/API: `/api/usb-transfer/*`, `transfer_folders`, module enter
- Production `index.html` + `app.js` Home tile and Transfer screen

## Next steps

- Manual check: Home → USB file transfer → MTP/ADB device → Start transfer
- Optional: mark draft PR ready when happy
