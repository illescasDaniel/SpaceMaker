_Last updated: 2026-09-23_

## Branch

`main`

## Current focus

Gallery UX and theming shipped on `main`; no active feature branch.

## Just changed (committed)

- Gallery item **Previous / Next** (timeline order) with self-hosted **Font Awesome** chevrons and grid-centered nav buttons
- **System light/dark** via shared `theme.css` on all web shells; removed module-based palette switching
- CSP `font-src 'self'`; Font Awesome noted in `docs/legal/THIRD_PARTY_TOOLS.md`

## Next steps

1. Manual: Gallery item nav + theme in light and dark OS settings (desktop + phone gallery QR)
2. Manual: iPhone USB extract → Stop extract → convert when count stable
3. Easy-mode import panels — await spec approval (separate track)

## Run

```bash
uv run task spacemaker
uv run task checks
```
