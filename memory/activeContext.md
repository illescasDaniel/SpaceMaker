_Last updated: 2026-09-28_

## Branch

`main`

## Current focus

Just merged the `/new-worktree` skill (from `worktree-new-worktree-skill`, forked from `main`): creates a
git worktree + branch always forked from the currently checked-out branch (never `main`), then
copies/regenerates `.venv` + `node_modules` from the primary checkout so a new worktree is immediately
usable — mirrors srxy's `copy-venv-to-worktree-srxy` skill plus worktree creation, adapted for
SpaceMaker's dual-stack (`uv` workspace + npm/Biome) and dual-tool (Claude Code `EnterWorktree` / Cursor
manual `git worktree add`) setup. Also fixed `apply-worktree`/`delete-worktree` to recognize
`.claude/worktrees/` targets, not just Cursor's `~/.cursor/worktrees/`. Verified end-to-end against the
real `gallery-thumb-fix` worktree before merge; three bugs found and fixed along the way (see
`decisions.md`).

Separately, the DNG-convert/missing-thumbnails/aspect-preserving-thumbnails work (`worktree-gallery-thumb-fix`)
is already merged into `main` (commit `8b7223d`) — code-complete, tests green, verified against the
user's real library. No outstanding follow-up beyond what's tracked in `progress.md`.

## Touched files (this merge)

- `.cursor/skills/new-worktree/SKILL.md`, `.cursor/skills/new-worktree/scripts/{copy-venv.sh,rewrite_venv_paths.py}` (new)
- `.cursor/skills/apply-worktree/SKILL.md`, `.cursor/skills/delete-worktree/SKILL.md` (`.claude/worktrees/` support)
- `AGENTS.md` (added `/new-worktree` to the user-invoked skills list)

## Next steps

1. Run `uv run task checks` on `main` post-merge to confirm the gate is green.
2. `worktree-new-worktree-skill` worktree is left in place (not deleted by this merge) — use
   `/delete-worktree` separately if/when it should be removed.
