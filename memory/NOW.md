# Now
Updated: 2026-11-17

## Doing
- Memory moved to `memory-1` and SDD to `sdd-html-feature` (agentic-loadout 0.8.0 upgrade, 2026-11-17). The old status
  and decisions are not migrated yet: until they are, the last recorded status is `memory/activeContext.md` (2026-10-22)
  and the open work list is `memory/progress.md`. Read both before starting work, checked against `git log`.
- Check before trusting the old bank: it says "Download all" (`specs/download-all/SPEC.md`) is uncommitted with its
  round-2 grade pending, but git has it committed (`c9537c4`, 2026-10-29) and released in 1.4.0. Whether round 2 ran is
  not recorded; if the user wants it, grade it with `code-grader` against that legacy spec.

## Done recently
- 2026-11-17: agentic-loadout 0.8.0 installed; agemem MCP and hooks removed; agents, workflow and `AGENTS.md` reconciled
  (uncommitted).

## Next
- Ask the user whether to migrate the old memory (activeContext/progress to NOW/LATER, each dated entry of
  `decisions.md` to a note under `memory/notes/`, `archive.md` and `friction/` kept as history). Keep the old files and
  `.agemem/` until the user confirms they can be removed.

## Open questions / blocked
- jevmem and agemem notes live outside the repo (`~/.jevmem/`, `.agemem/local/`); exporting them into notes needs the
  user's go-ahead.
