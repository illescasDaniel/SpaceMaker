_Last updated: 2026-09-29_

## Branch

`main` (up to date with `origin/main` before this commit)

## Current focus

Quality-gate fixes just landed; smoke items from earlier gallery/shell work still pending.

## Next steps

1. Hard-reload the desktop shell — confirm no horizontal jump on load.
2. Restart SpaceMaker (full quit) and smoke gallery — leave "Loading more", tiles show, console clean.

## Just changed

- `ui_shell.py`: ruff format
- MCP tests: unique `test_codenav_server.py` / `test_webnav_server.py` basenames
- Media convert unit tests: `path_fallback_allowed=False` against system `avifenc`
