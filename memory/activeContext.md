_Last updated: 2026-09-29_

## Branch

`main`

## Current focus

Stray `-version` fix committed (tool_runner path-fallback gate + stub regression tests).

## Next steps

Open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).

## Just changed

- `tests/unit/test_progressive_avif_encode.py`: stubs exit early on `-version` so they don't treat it as an output path.
- `src/spacemaker/adapters/outbound/media/tool_runner.py`: magick system fallback only when `path_fallback_allowed`.
- `tests/unit/test_tool_runner.py`: regression — no cwd/`-version` when fallback disallowed; broken managed prefers system when allowed.
- Deleted untracked repo-root `-version` (content was `avif`).

## Open items

None for this thread.
