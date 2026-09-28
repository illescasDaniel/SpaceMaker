_Last updated: 2026-09-28_

## Branch

`claude/thumbnail-aspect-ratio-15f161` (worktree `thumbnail-aspect-ratio-5b1cfd`), forked from `main`
(which includes the `8b7223d` DNG-convert/aspect-preserving-thumbnails fix and the merged `/new-worktree`
skill).

## Current focus

Diagnosed why the user still saw square/stale thumbnails after `8b7223d`: the fix was correct, but the
desktop webview's persistent HTTP cache and the server's mtime-only disk cache both kept serving pre-fix
bytes. Full SDD (wireframe → spec → architecture → tests → impl) approved in chat 2026-09-28 and shipped:

- `/thumbs/` now `Cache-Control: no-cache` + `ETag`/304 revalidation (was `max-age=86400`, unversioned).
- On-disk `.thumbnails/` cache now invalidates on a thumbnail-generator version change, not just mtime.
- New Settings → **Clear browser cache** action (no confirm) as the manual escape hatch for the webview's
  persistent HTTP cache.
- `/media/` deliberately left on long-lived caching for now (real savings there; revisit only if it shows
  the same staleness bug).

See `memory/progress.md` for the full file-by-file list. `uv run task checks` green on every file touched
this session; Biome clean on the production files touched (`index.html`, `app.js`). Live-verified against
the running `--server-only` app (Settings → Clear browser cache renders, calls the API, shows feedback).

Separately, per the user's request mid-session ("fix existing main bugs"), spawned a background subagent
(own worktree, off `main`) to fix the pre-existing `ruff format` / Windows path-separator pytest / Biome
CRLF+lint failures tracked as their own `progress.md` item — unrelated to this branch's work, not yet
reported back as of this write.

## Touched files (this session)

- `src/spacemaker/application/clear_browser_cache.py` (new) — `ClearBrowserCache` use case
- `src/spacemaker/bootstrap/services.py` — wires `ClearBrowserCache`
- `src/spacemaker/bootstrap/ui_shell.py` — `THUMB_CACHE_HEADERS`, `file_etag()`
- `src/spacemaker/domain/gallery_cache_paths.py` — `thumbnail_format_version_marker_path()`
- `src/spacemaker/adapters/outbound/media/subprocess_thumbnails.py` — `THUMBNAIL_FORMAT_VERSION` check
- `src/spacemaker/adapters/inbound/web/app.py` — `/thumbs/` 304 handling, `POST /api/browser-cache/clear`
- `src/spacemaker/adapters/inbound/web/static/{index.html,app.js}` — Settings UI + handler
- `wireframes/app.html` — Settings wireframe for Clear browser cache
- `specs/gallery/SPEC.md`, `specs/home-modules/SPEC.md` — spec updates
- `tests/unit/{test_subprocess_thumbnails,test_thumb_route,test_clear_prefs_and_reset_library}.py`

## Next steps

1. Not yet committed on this branch — commit this session's work.
2. Consider opening a PR once committed (not yet discussed with the user).
3. Check back on the background "fix existing main bugs" subagent's result branch; merge or review
   separately from this branch's work.
