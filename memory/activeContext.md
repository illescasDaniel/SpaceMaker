_Last updated: 2026-09-28_

## Branch

`feature/cleaner_code`

## Current focus

Merged latest `origin/main` into this branch (quality-gate fixes, stale-thumbnail cache busting,
`/new-worktree` skill, DNG/convert atomic writes + logging). Ported main's cache-bust work into the
modular layout (`routes/media.py`, `routes/settings.py`, `bootstrap/services/`, `web/src/settings.ts`).

## Next steps

1. Manual smoke: desktop shell + mobile gallery (`/static/js/main.js`); Settings → Clear browser cache.
2. Optionally strip `@ts-nocheck` from feature modules over time.
3. Open PR when smoke looks good.

## Just changed

- Merge `origin/main` → `feature/cleaner_code` (conflicts resolved onto split routers / TS shell / aiosqlite)
