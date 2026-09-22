---
name: save-changes
description: >-
  Update agent memory, stage project changes, commit, and push to the tracked
  remote. Use when the user invokes /save-changes or asks to save-changes.
disable-model-invocation: true
---

# Save Changes

Use only when the user explicitly invokes `/save-changes` (or clearly asks to save-changes).

## Goal

Hand off a dirty tree: refresh `memory/`, commit, push. Do **not** force-push, skip hooks, amend unless the usual amend conditions are met, or change git config.

## Steps

1. **Memory (before staging)**
   - Follow `.cursor/rules/agent-memory.mdc`.
   - `progress.md` — check off completed work; add newly discovered tasks/bugs. Do not invent worktree-cleanup tasks.
   - `activeContext.md` — rewrite so the next session can start: branch, focus, just changed, next steps, no stale blockers.
   - `decisions.md` — append-only, newest first, only for significant technical choices made in this work. Skip if none.
   - Include these memory edits in the same commit as the code.

2. **Review**
   - Parallel: `git status`, `git diff` (staged + unstaged), `git log` (recent messages for style), `git status -sb` (upstream).
   - Do not stage secrets (`.env`, credentials files, API keys). Warn if the user asked to commit those.

3. **Stage and commit**
   - Stage relevant tracked/untracked files (`git add` paths; no `-i`).
   - If there is nothing to commit, skip to push (or stop if also nothing to push).
   - Message: 1–2 sentences on **why**, matching this repo’s log (sentence case, no conventional-commit prefix unless the branch already uses it). HEREDOC only:

     ```bash
     git commit -m "$(cat <<'EOF'
     Commit message here.

     EOF
     )"
     ```

4. **Push**
   - `git push` to the tracked remote. If no upstream: `git push -u origin HEAD`.
   - Never `--force`, `--no-verify`, or `--no-gpg-sign`.
   - `git status -sb` after push and report the commit SHA plus remote result.

## Rules

- Never update git config.
- Never amend unless the user asked, HEAD is this conversation’s commit, and it has not been pushed.
- If a hook rejects the commit, fix and create a **new** commit (do not amend).
- Do not push to `main`/`master` with `--force`. Warn if they ask to force-push those branches.
