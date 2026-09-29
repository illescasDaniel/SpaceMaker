_Last updated: 2026-09-29 (MCP review round 2 + worktree-aware workspace, branch `feature/mcp-improvements`)_

## Branch

`feature/mcp-improvements` (from `main`; contains everything from the former `worktree-review-custom-mcp-tools`). Check this branch out in the **primary** checkout so the MCP servers run the new code (they always run from the primary's `.venv`/source).

## Current focus

Finish and verify the MCP tooling work, then merge to `main`.

Done and tested (609 tests, `uv run task checks` green):
- Review round 2 fixes for codenav/webnav (see `progress.md`).
- Worktree support: `WorkspaceSelector` (pinned env > client `roots/list` in same repo > `CLAUDE_PROJECT_DIR`/cwd), `workspace` tool on both servers, `.mcp.json` no longer pins the workspace env. Rationale + limits: `decisions.md` 2026-09-29 "MCP servers pick the workspace per request".

## Next steps (pick up here)

1. Primary checkout: `git switch feature/mcp-improvements`, then restart the MCP servers (they only pick up code on restart).
2. Verify the new code is live: `implementations` schema now has `file_path`; call the `workspace` tool of codenav and webnav (should report the primary path, source `CLAUDE_PROJECT_DIR`).
3. Worktree verification: DONE (desktop app answers roots/list). Optionally repeat in Cursor (pinned via `${workspaceFolder}`).
4. Optional cleanups noticed: none blocking. A tool call racing a workspace switch can fail once (documented).
5. Merge `feature/mcp-improvements` into `main`; .

## Older open items

- Trial `code-grader` on the next real SDD feature.
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json`.
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).
