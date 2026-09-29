_Last updated: 2026-09-29_

## Branch

`cursor/cleaner-code-with-main-2bd1` (draft PR #6 into `main`)

## Current focus

Gallery / shell-cache fix committed: auto JS fingerprint + import map, `R.*` registry aliases, bare-ref fixes, WebEngine HTTP cache clear on launch.

## Next steps

1. Restart SpaceMaker (full quit) and smoke gallery — should leave "Loading more" and show tiles; console clean.
2. Review / merge draft PR #6 when ready.

## Just changed

- Shell `R.api` / `bindInfoPanelToggle` / `setQrImageSrc` aliases; qualify bare `applyState`/`pushSettings`/`loadServerInfo`
- Auto `UI_SHELL_VERSION` fingerprint + import map; fixed webengine profile `default`; clear HTTP caches on launch
- Gallery timeline defensive fetch so spinner cannot stick
