_Last updated: 2026-09-26_

## Branch

`cursor/usb-file-transfer-c861`

## Current focus

**USB file transfer** — new Home module (SDD). Phase 0 wireframe only.

Interpreted user “afp” as **AFC / iPhone USB** (same stack as USB photo backup), not network AFP.

## Just changed

- `wireframes/app.html` — USB file transfer polish per design feedback: no step “1”; iPhone limit banner only on AFC; destination / mode / pause-stop copy behind ⓘ panels
- Earlier: Home tile + `#view-usb-file-transfer`; `wireframes/README.md`; memory

## Next steps

1. **Stop for design approval** — user reviews wireframe, replies wireframe approved (or changes).
2. After approval → Phase 1 `specs/usb-file-transfer/SPEC.md` only, then stop again.

## Run

```bash
xdg-open wireframes/app.html
# then tap “USB file transfer” on the Home hub
```
