# Later
## Real-device checks
- 2026-10-01 (User) Confirm the native Windows backend (edgechromium) opens a working window on real hardware ([note](notes/native-pywebview-win-mac.md)).
- 2026-10-18 (User) Try gallery batch in a real browser and desktop shell: select, trash, convert, CPU confirm ([note](notes/gallery-batch-trash-and-cpu-export.md)).
- 2026-10-21 (User) Check the phone picker on a real phone: grid tiles, Space on a thumbnail, scroll anchor, narrow width, sort menu ([note](notes/phone-picker-grid-view-resolution.md)).
- 2026-10-21 (User) Check phone picker previews on a real iPhone (AFC); only Android was tried ([note](notes/phone-raw-dng-preview-ifd-parser.md)).
- 2026-10-29 (User) Check Download all on a real phone: share.html and transfer.html.
## Agent tooling
- 2026-10-22 (User) Close the three `memory/friction/2026-10-22-agent-guild-*` entries once their upstream fixes are published.
## App
- 2026-09-23 (User) Decide whether to add buttons to open folders for failed or unsupported image imports in Easy mode; the counts already display, but the approved folder actions are absent.
## Suggestions
- 2026-11-17 Consider a real send2trash integration test when touching trash operations (legacy progress item).
- 2026-11-17 Add sha256 pins to `packaging/tool-catalog.json` before the next release: downloads are unverified ([note](notes/pre-1-0-deliberately-left-open.md)).
- 2026-11-17 Add a 401-under-passcode test for the LAN-reachable gallery batch routes when next touching them: a regression would expose delete ([note](notes/gallery-batch-trash-and-cpu-export.md)).
