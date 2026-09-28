_Last updated: 2026-09-28_

## Branch

`feature/cleaner_code`

## Current focus

**Code modernization** on branch; quality gate fixed for native Windows.

## Next steps

1. Manual smoke: desktop shell + mobile gallery (`/static/js/main.js`).
2. Optionally strip `@ts-nocheck` from feature modules over time.
3. Open PR when smoke looks good.

## Just changed

- `checks.py` runs the gate natively (no bash / WSL stub); `web.sh --fix` → `npm run format`
