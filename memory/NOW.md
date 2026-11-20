# Now
Updated: 2026-11-17 (migration session; no session export)

## Doing
- macOS test fixes on feature/macOS: type checking and tests pass; npm audit remains blocked by the unpatched picomatch advisory GHSA-fc5q-39xc-vjpf.
- Migrated project memory and documentation; old project memory files moved to trash with user approval.

## Done recently
- 2026-11-17: memory migration: 151 notes (37 superseded) in 9 topics from `decisions.md`, jevmem/agemem and
  `friction/`; open items moved to `LATER.md` ([note](notes/memory-1-replaces-memory-bank-jevmem.md)).
- 2026-11-17: agentic-loadout 0.8.0 installed, agemem removed (commit 09f8750).
- 2026-10-29: Download all button on Send/Transfer pages (c9537c4), released in 1.4.0.
- 2026-10-21: phone picker grid view and RAW (DNG) previews (7fc658a, b18b341), released in 1.3.0.

## Next
- Keep the real Windows desktop test in `LATER.md`.

## Open questions / blocked
- Download all: the old bank says grader round 2 was pending; git shows it committed and released in 1.4.0. Whether
  round 2 ran is not recorded. Grade it with `code-grader` against `specs/download-all/SPEC.md` if wanted.
