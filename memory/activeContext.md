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
3. **Worktree verification (the open question):** start a session in a linked worktree (e.g. `/new-worktree`), call `workspace` on both servers. Expect the worktree path with source `client roots`.
   - If it still reports the main checkout: the Claude desktop app does not send/answer `roots/list` (or speaks the 2026-07-28 era where servers cannot request roots). Then add a different channel, e.g. accept a `workspace` hint derived from absolute `file_path` arguments, or an explicit per-session pin; record the finding in `memory/friction/`.
   - Note `.mcp.json` is read from the *primary* checkout, so changes to it made inside a worktree have no effect until merged.
4. Optional cleanups noticed: none blocking. A tool call racing a workspace switch can fail once (documented).
5. When verified: merge `feature/mcp-improvements` into `main`; update `progress.md` (remove the "Open: verify" note).

## Older open items

- Trial `code-grader` on the next real SDD feature.
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json`.
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).
