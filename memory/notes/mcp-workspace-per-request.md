---
name: mcp-workspace-per-request
description: Claude Code starts MCP servers once from the main checkout, so servers pick the workspace per request
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

MCP servers pick the workspace per request (worktree support).

- **Context:** Claude Code starts codenav/webnav once with the *main* checkout as `CLAUDE_PROJECT_DIR`/cwd (and reads `.mcp.json` from there), even for sessions in a linked worktree, so a fixed root answered from the wrong tree. Env vars cannot carry the worktree; a per-worktree `.env` would be manual.
- **Decision:** `mcp_nav_shared.workspace.WorkspaceSelector`: pinned `*_MCP_WORKSPACE` (Cursor keeps `${workspaceFolder}`) > client MCP `roots/list` (only roots of the same repo, compared via the shared common dir) > `CLAUDE_PROJECT_DIR`/cwd. Every tool takes an optional `Context` and calls `_use_workspace(ctx)`; on change the server stops its language server(s), clears caches and re-derives root-relative config. `.mcp.json` no longer pins the workspace env. Each server has a `workspace` tool reporting the active root and why.
- **Rationale:** roots is the sanctioned client-to-server channel; the same-repo guard stops unrelated roots hijacking the server. Limits: needs a handshake-era client that answers `roots/list` (the 2026-07-28 revision deprecates roots); not yet verified against the real Claude desktop client — check with the `workspace` tool in a worktree session after merge + MCP restart.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — MCP servers pick the workspace per request (worktree support)".
