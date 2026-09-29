_Last updated: 2026-09-29 (friction backlog cleared + worktree dependency sync, branch `claude/friction-fixes`)_

## Branch

`claude/friction-fixes` (off `main`@`7bfea9e`), applied to `main` via `/apply-worktree`; not pushed.

## Current focus

Agent-tooling hygiene: every `memory/friction/` entry is now `fixed`; `copy-venv.sh` keeps worktree `.venv`/`node_modules` in sync with the lockfiles.

## Next steps

- Trial `code-grader` on the next real SDD feature (confirm the Cursor agent loads).
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json` (untested: lockfiles were identical when written).
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).
- If app-made worktrees keep forking from an old commit, check the `worktree.baseRef` setting (`head` vs `fresh`).

## Just changed

- AGENTS.md: copy-paste MCP example calls (`selector(name=…)`), subagent-prompt rule, "Worktree dependencies" section.
- codenav/webnav tool docstrings lead with the question they answer; `selector`/`css_var` accept `query` as an alias for `name`.
- `docs/agent-tooling.md`: hidden Browser pane never advances CSS transitions.
- `new-worktree/scripts/copy-venv.sh`: kept `.venv` is re-`uv sync`ed; `node_modules` is lock-stamped, copied only when lockfiles match, else `npm ci`. Gate errors point at the script.
