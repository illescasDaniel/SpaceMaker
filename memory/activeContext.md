_Last updated: 2026-09-26_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Phase 0 (wireframe)** — Photo backup “Compress media” preference checkbox + info button.

Wireframe updated in `wireframes/app.html` (`#view-easy`):
- Checkbox **Compress media** (default on)
- ⓘ info panel: why (save space + web-compatible) + how (AVIF / AV1 when HW available)
- Tools-unavailable: forced off + disabled + hint
- Convert progress hidden when off; short “Compression off” status
- Demo: **Cycle convert preference** (on → off → tools missing)

## Blockers

Waiting for **explicit wireframe approval** in chat before Phase 1 (spec).

## Next steps

1. User reviews `wireframes/app.html` Photo backup screen → reply **wireframe approved** (or change requests).
2. Phase 1: update `specs/easy-mode/SPEC.md` (and related convert/settings preference persistence).

## Just changed

- `wireframes/app.html` — convert preference UI on Photo backup
- `memory/activeContext.md`, `memory/progress.md`
