_Last updated: 2026-09-28_

## Branch

`worktree-new-worktree-skill` (forked from `main`, per user request — unrelated to `feature/cleaner_code`'s in-progress work)

## Current focus

New `/new-worktree` skill: creates a git worktree + branch for a new task (always forked from the
currently checked-out branch, never `main`), then copies/regenerates `.venv` + `node_modules` from the
primary checkout so the worktree is immediately usable. Mirrors srxy's
`copy-venv-to-worktree-srxy` skill plus worktree creation, adapted for SpaceMaker's dual-stack
(`uv` workspace + npm/Biome) and dual-tool (Claude Code `EnterWorktree` / Cursor manual
`git worktree add`) setup. Also fixed `apply-worktree`/`delete-worktree` to recognize
`.claude/worktrees/` targets, not just Cursor's `~/.cursor/worktrees/`.

## Touched files

- `.cursor/skills/new-worktree/SKILL.md` (new)
- `.cursor/skills/new-worktree/scripts/copy-venv.sh` (new)
- `.cursor/skills/new-worktree/scripts/rewrite_venv_paths.py` (new, adapted from srxy)
- `.cursor/skills/apply-worktree/SKILL.md`, `.cursor/skills/delete-worktree/SKILL.md` (`.claude/worktrees/` support)
- `AGENTS.md` (added `/new-worktree` to the user-invoked skills list)

## Next steps

1. Verify `copy-venv.sh` against the real `.claude/worktrees/gallery-thumb-fix` worktree (already has a
   populated `.venv`/`node_modules` to copy from/over).
2. Run `uv run task checks` from a synced worktree to confirm the full gate passes on copied deps.
3. Hand off for review/PR from this worktree; do not merge into `feature/cleaner_code` or `main` without
   the user's say-so.
