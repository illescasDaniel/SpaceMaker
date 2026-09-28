_Last updated: 2026-09-28_

## Branch

`feature/cleaner_code` (also tip `cursor/cleaner-code-with-main-2bd1` → draft PR #6 into `main`)

## Current focus

Merged latest `origin/main` into this branch. Ported cache-bust / Clear browser cache onto the
modular layout. `uv run task checks` green.

## Next steps

1. Manual smoke: desktop shell + mobile gallery; Settings → Clear browser cache.
2. Optionally strip `@ts-nocheck` from feature modules over time.
3. Review / merge draft PR #6 when ready.

## Just changed

- Merge `origin/main` → `feature/cleaner_code`; ty fix for Qt message handler `str | None`
