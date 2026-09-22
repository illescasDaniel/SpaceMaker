_Last updated: 2026-09-22_

## Branch

`main` — unpushed commits after `efa4223`; push skipped per user.

## Current focus

Gallery item UX polish and desktop host-open actions.

## Just changed (this commit)

- Desktop: **Open** / **Open containing folder**, friendly export, Delete; preview **max-height 55vh**
- Phone gallery: Download + friendly + Delete (Share removed)
- `/json/version` stub for Qt WebEngine log noise
- Reverted HTML `Cache-Control: no-cache` (keep default caching for responsiveness)

## Next steps

1. Manual smoke: desktop Open/folder, gallery delete, item preview height
2. Phase 4 packaging (open)

## Run

```bash
uv run task spacemaker
uv run task checks
```
