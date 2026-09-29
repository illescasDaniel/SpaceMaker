_Last updated: 2026-09-29_

## Branch

`claude/thumbnail-304-requests-5afc35`

## Current focus

Stop 304 flood on /thumbs/ — complete.

## Next steps

Ready to apply to main via /apply-worktree.

## Just changed

- `src/spacemaker/bootstrap/ui_shell.py`: changed `THUMB_CACHE_HEADERS` from `no-cache` to `max-age=300, must-revalidate`. Root cause: `loadGallery()` clears and re-creates all `<img>` elements on each navigation; `no-cache` forced a conditional GET (304) per visible thumbnail every time.

## Open items

None. Branch ready to apply.
