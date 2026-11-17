# Now
Updated: 2026-11-17 (migration session; no session export)

## Doing
- Legacy memory migrated into memory-1 notes and topic pages; project docs given docs-1 frontmatter with a generated
  index. Uncommitted, waiting for the user's review.

## Done recently
- 2026-11-17: memory migration: 151 notes (37 superseded) in 9 topics from `decisions.md`, jevmem/agemem and
  `friction/`; open items moved to `LATER.md` ([note](notes/memory-1-replaces-memory-bank-jevmem.md)).
- 2026-11-17: agentic-loadout 0.8.0 installed, agemem removed (commit 09f8750).
- 2026-10-29: Download all button on Send/Transfer pages (c9537c4), released in 1.4.0.
- 2026-10-21: phone picker grid view and RAW (DNG) previews (7fc658a, b18b341), released in 1.3.0.

## Next
1. (User) Review the migrated notes and docs frontmatter, then say whether to commit.
2. (User) Decide whether the legacy files can be removed: `memory/activeContext.md`, `progress.md`, `decisions.md`,
   `archive.md`, `memory/README.md`, `.agemem/`, and the `project:spacemaker` notes in `~/.jevmem/memory.db`.

## Open questions / blocked
- `LATER.md` has two (User) lines older than 30 days: the Windows edgechromium check (2026-10-01) and the Easy mode
  import-issues decision (2026-09-23). Keep or drop each?
- Download all: the old bank says grader round 2 was pending; git shows it committed and released in 1.4.0. Whether
  round 2 ran is not recorded. Grade it with `code-grader` against `specs/download-all/SPEC.md` if wanted.
