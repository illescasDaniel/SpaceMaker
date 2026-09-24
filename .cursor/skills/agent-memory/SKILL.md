---
name: agent-memory
description: Update SpaceMaker memory bank and session hand-off. Use at session start, milestones, and before ending work with progress.
---

# Agent Memory Skill

Per-branch project state lives in `memory/` (git-tracked, so it follows the branch). Summary in `AGENTS.md` "Memory bank"; this is the full protocol.

## Files

| File | Role |
|------|------|
| `memory/progress.md` | Macro checklist — what is done, what is pending, open bugs. |
| `memory/activeContext.md` | Micro scratchpad — current focus, active blockers, touched files, immediate next steps. |
| `memory/decisions.md` | Technical log — significant technical, structural, or dependency decisions and their rationale (newest first, append-only). |
| `memory/archive.md` | Finished history moved out of `activeContext.md`/`progress.md` — not read at session start. |

## Session start

1. Read `memory/activeContext.md`
2. Read `memory/progress.md`

## During work — update only on these triggers

- **`progress.md`** — a task is completed (`[ ]` → `[x]`), or a new task/bug is discovered.
- **`activeContext.md`** — switching focus, hitting a blocker, or concluding work/a step (log modified files, current state, exact next step).
- **`decisions.md`** — a significant technical/structural/dependency choice: append with context + decision + rationale.

**Never** add worktree cleanup/deletion tasks to tracked memory — that's per-developer local hygiene and creates merge noise.

## Keeping activeContext.md lean

`activeContext.md` is a scratchpad, not a log — keep it to roughly the current thread (branch, focus, blockers, next steps, a short "just changed" list). When a thread concludes (its next steps are done, or focus has moved on), move it to `memory/archive.md` under a dated heading rather than letting it accumulate. `progress.md` should list only genuinely open items plus the current in-flight feature's Done list — move a finished feature's Done list to `archive.md` once nothing in it is likely to be referenced again.

## Hand-off

Before finishing a turn with progress:

1. Checkbox state in `progress.md` is accurate.
2. `activeContext.md` states the exact next step for the next session.

## Version control

`memory/` is tracked, per-branch — each worktree/checkout carries its branch's version.

- Commit memory updates at milestones (with feature commits or a `memory:` commit); don't leave the tree permanently dirty.
- `decisions.md`: append-only, never cleaned, newest first.
- `archive.md`: append-only in spirit (don't delete old entries), but not read at session start.

## Branch init

When the user starts a new feature branch/worktree and asks to initialize memory:

1. `progress.md` — new section header for the feature/version; empty Done; carry forward only relevant Open items.
2. `activeContext.md` — rewrite: branch name, focus = new feature, no blockers, only relevant next steps.
3. `decisions.md` — untouched.

Commit the initialization in the branch's first commit.

## On merge

Keep the feature branch's `progress.md`/`activeContext.md` (superset); merge `decisions.md` carefully (append-only, both sides' entries kept, newest first).
