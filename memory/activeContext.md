_Last updated: 2026-09-29_

## Branch

`cursor/cleaner-code-with-main-2bd1` (draft PR #6 into `main`)

## Current focus

Scrollbar layout-jump fix ready to smoke; gallery shell-cache fix still awaiting restart smoke.

## Next steps

1. Hard-reload the desktop shell — confirm no horizontal jump on load.
2. Restart SpaceMaker (full quit) and smoke gallery — leave "Loading more", tiles show, console clean.
3. Review / merge draft PR #6 when ready.

## Just changed

- `theme.css`: `html { scrollbar-gutter: stable }`
- `.app-main` gutter in `shell-layout.css` + `wireframes/app.html`
- Inline critical CSS in `index.html` head (hide screens / body overflow before linked CSS)
