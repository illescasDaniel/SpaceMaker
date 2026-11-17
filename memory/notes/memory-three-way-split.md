---
name: memory-three-way-split
description: state in the memory bank, durable facts in jevmem, rules in AGENTS.md
type: decision
date: 2026-10-03
status: superseded
supersedes:
superseded_by: memory-1-replaces-memory-bank-jevmem
source:
---

Three-way split between memory bank, jevmem and AGENTS.md.

- **Context:** the jevmem trial put a second memory store next to `memory/`. jevmem had picked up a copy of `activeContext.md`'s next steps (a note that goes stale silently) and restatements of AGENTS.md rules.
- **Decision:** current state → `memory/activeContext.md` / `progress.md` (never jevmem); dated facts that stay true → jevmem; rules → `AGENTS.md`. Significant decisions keep their `decisions.md` entry and also get a one-fact jevmem note. Written into `AGENTS.md` "Memory bank", the agent-memory skill and the jev-memory skill (same rule now recommended in the jevmem README).
- **Rationale:** the markdown bank is small, read whole, per branch and reviewed in PRs; jevmem holds too many facts to read whole and is recalled by relevance, but is not per branch and nothing marks a status note outdated. Overlap only hurts when the copied text can go stale.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-03 — Three-way split between memory bank, jevmem and AGENTS.md".

Superseded by [memory-1-replaces-memory-bank-jevmem](memory-1-replaces-memory-bank-jevmem.md).
