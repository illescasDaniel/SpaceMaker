_Last updated: 2026-09-26_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Phase 0 (wireframe)** — Photo backup “Convert media” preference checkbox + info button.

Wireframe updated in `wireframes/app.html` (`#view-easy`):
- Checkbox **Convert media** (default on)
- ⓘ info panel: photos → AVIF; videos → AV1 when HW encoding available
- Tools-unavailable: forced off + disabled + hint
- Convert progress hidden when off; short “Conversion off” status
- Demo: **Cycle convert preference** (on → off → tools missing)

## Blockers

Waiting for **explicit wireframe approval** in chat before Phase 1 (spec).

## Next steps

1. User reviews `wireframes/app.html` Photo backup screen → reply **wireframe approved** (or change requests).
2. Phase 1: update `specs/easy-mode/SPEC.md` (and related convert/settings preference persistence).

## Just changed

- `wireframes/app.html` — convert preference UI on Photo backup
- `memory/activeContext.md`, `memory/progress.md`
