_Last updated: 2026-09-22_

## Branch

`main` — commit `521a90b`; push skipped per user.

## Current focus

Gallery item actions + mobile gallery header polish.

## Just changed

- Mobile gallery header: **SpaceMaker Gallery** left, Timeline/Calendar right (wrap when tight)
- Gallery item: **On disk** path, **Delete**, **Share** (friendly export + `navigator.share` with download fallback)

## Next steps

1. Manual smoke: delete/share/path on desktop; Share on iOS Safari / Android Chrome
2. Phase 4 packaging (open)

## Run

```bash
uv run task spacemaker
uv run task checks
```
