---
name: memory-1-replaces-memory-bank-jevmem
description: memory-1 replaced the memory bank, jevmem and agemem; old files kept as history until the user approves removal
type: decision
date: 2026-11-17
status: current
supersedes: jevmem-0-4-config-file
superseded_by:
source:
---

Project memory now follows the `memory-1` skill: `memory/NOW.md`, `LATER.md`, `MEMORY.md`, `notes/` and `topics/`. This happened in the agentic-loadout 0.8.0 upgrade (commit 09f8750, 2026-11-17), which also removed the agemem MCP and hooks; `.mcp.json` now has only `codenav` and `webnav`, so jevmem is no longer configured either.

History: the per-branch memory bank (`activeContext.md`, `progress.md`, `decisions.md`, `archive.md`) dates from 2026-09-22; jevmem was added on 2026-10-03 (see memory-three-way-split); an agemem store (`.agemem/local/notes.sqlite`, created 2026-11-13) held the same 80 notes as jevmem's `project:spacemaker` scope.

The migration into notes was done on 2026-11-17 at the user's explicit request: each `decisions.md` entry became a note with its original date and text; jevmem/agemem facts that were not already in `decisions.md` became notes; facts that only restate `AGENTS.md` rules were not copied. `memory/friction/` stays in use as the tooling-friction log (AGENTS.md).

**Why:** not recorded beyond the commit ("Update project agent workflow to loadout 0.8").
**How to apply:** keep `activeContext.md`, `progress.md`, `decisions.md`, `archive.md`, `README.md`, `.agemem/` and the `project:spacemaker` notes in the shared jevmem database until the user says they can be removed; never delete the shared database as a whole; do not write new entries to them.

Also replaces: [memory-three-way-split](memory-three-way-split.md).
