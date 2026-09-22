---
name: agent-memory
description: Update SpaceMaker memory bank and session hand-off. Use at session start, milestones, and before ending work with progress.
---

# Agent Memory Skill

Always-on rule: `.cursor/rules/agent-memory.mdc`.

## Session start

1. Read `memory/activeContext.md`
2. Read `memory/progress.md`

## During work

Update only on triggers in the rule:

- **progress.md** — task completed or new task discovered
- **activeContext.md** — focus change, blocker, or hand-off
- **decisions.md** — significant technical decision (append, newest first)

## Hand-off

Before finishing a turn with progress:

1. Checkbox state in `progress.md` is accurate
2. `activeContext.md` states the exact next step for the next session

## Branch init

When user starts a new feature branch: reset `progress.md` section and rewrite `activeContext.md`; never truncate `decisions.md`.
