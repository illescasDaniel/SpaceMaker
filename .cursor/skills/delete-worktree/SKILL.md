---
name: delete-worktree
description: >-
  Remove the current isolated Git worktree and clean up its branch when finished.
  Use when the user invokes /delete-worktree or asks to delete/remove the
  agent worktree checkout.
disable-model-invocation: true
---

# Delete Worktree

Use only when the user explicitly invokes `/delete-worktree` (or clearly asks to delete this worktree).

## Goal

Unregister the isolated checkout from git and drop its generated `cursor/...` (Cursor) or `worktree-...` (Claude Code's `EnterWorktree`/`/new-worktree`) branch after work is finished or applied. Does **not** apply changes (that is `/apply-worktree`).

## Expected lock (do not escalate)

The **same Cursor agent tab** that ran in the worktree often still has that folder as an open workspace root or has files/terminals open under it. On Linux/macOS this commonly yields:

- `error: failed to delete '…/.cursor/worktrees/…': Permission denied`
- `rm: …: Directory not empty` / “Resource busy”

That is **normal**. Success for this skill is:

1. The worktree no longer appears in `git worktree list`, and
2. The generated `cursor/…`/`worktree-…` branch is deleted when appropriate.

An empty or nearly empty leftover directory under `~/.cursor/worktrees/…` is **OK**. Report it briefly and stop. Do **not**:

- Kill Cursor/IDE processes, force-close handles, or run `lsof`/`kill` loops
- Loop on `rm -rf` retries
- Ask the user to restart the IDE unless they want the folder gone for disk cleanup

## Steps

1. **Confirm context**
   - `git rev-parse --show-toplevel`, `git worktree list`, current branch.
   - Identify the worktree path to remove (under `~/.cursor/worktrees/` for Cursor, or `.claude/worktrees/` for Claude Code's `EnterWorktree`/`/new-worktree`).
   - Abort if the target is the primary checkout (not under `~/.cursor/worktrees/` or `.claude/worktrees/`).

2. **Move out of the worktree**
   - **Claude Code**: if this session is inside the worktree because it called `EnterWorktree`, prefer `ExitWorktree({action: "remove", discard_changes: <true only if the user confirmed discarding pending changes>})` — it moves the session out, removes the worktree, and drops its branch in one step; then skip steps 3–4 below (already done) and go to step 5. If the session is instead just operating on a `.claude/worktrees/...` path without having called `EnterWorktree` in this session, do steps 3–4 manually.
   - **Cursor**: call `move_agent_to_root` (cursor-app-control MCP) on the main checkout path **before** removing anything (so the agent is not left inside a deleted root), then do steps 3–4 manually.

3. **Remove the worktree registration**
   - From the main checkout: `git worktree remove <worktree-path>` (use `--force` if the worktree still has leftover dirty files and the user asked to delete).
   - If git reports permission denied on deleting the directory but the worktree disappears from `git worktree list`, treat registration as done. Run `git worktree prune` once if needed.
   - Do not keep retrying filesystem deletes when the folder is locked by this Cursor/Claude Code tab.

4. **Optional branch cleanup**
   - If the worktree used a generated `cursor/...` or `worktree-...` branch, delete it with `git branch -d` / `-D` from the main checkout.
   - Do not delete `main` / `master` / the user's long-lived feature branch.

5. **Report**
   - State that the worktree is unregistered, whether its branch was deleted, and that the agent root is the main checkout.
   - If a leftover empty/locked folder remains, say so in one line — that is acceptable.

## Rules

- Never delete the primary checkout (the entry not under `~/.cursor/worktrees/` or `.claude/worktrees/`).
- Never force-push. Never update git config.
- Do not apply/merge changes as part of this skill.
- Do not fight OS file locks from the open agent tab.
- `ExitWorktree` with `action: "remove"` requires `discard_changes: true` if the worktree has uncommitted files or unmerged commits — only pass that after the user has confirmed discarding them; otherwise use `/apply-worktree` first.
