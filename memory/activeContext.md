_Last updated: 2026-09-26_

## Branch

`cursor/usb-file-transfer-c861`

## Current focus

**USB file transfer** — new Home module (SDD). Phase 0 wireframe only.

Interpreted user “afp” as **AFC / iPhone USB** (same stack as USB photo backup), not network AFP.

## Just changed

- `wireframes/app.html` — Home tile + `#view-usb-file-transfer` (MTP / ADB / iPhone USB; no convert; Documents destination)
- `wireframes/README.md` — mention fifth module
- `memory/activeContext.md`, `memory/progress.md`

## Next steps

1. **Stop for design approval** — user reviews wireframe, replies wireframe approved (or changes).
2. After approval → Phase 1 `specs/usb-file-transfer/SPEC.md` only, then stop again.

## Run

```bash
xdg-open wireframes/app.html
# then tap “USB file transfer” on the Home hub
```
