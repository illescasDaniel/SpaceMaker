# mcp-nav-shared

Shared helpers for the [`codenav-mcp`](../codenav_mcp/README.md) and
[`webnav-mcp`](../webnav_mcp/README.md) MCP servers. This package is **not**
an MCP server itself.

## What it provides

| Module | Role |
|--------|------|
| `mcp_nav_shared.lsp_client` | JSON-RPC/LSP subprocess client (`LspClient`): framing, request dispatch, document sync, scratch documents |
| `mcp_nav_shared.resolve` | Name-based symbol resolution (`resolve_symbol`, dotted `Class.method`, ambiguity errors) |
| `mcp_nav_shared.format` | Location headers (`path:line:col`), snippets, compact references / diagnostics lists |
| `mcp_nav_shared.workspace` | Workspace-root discovery from env vars / install path |
| `mcp_nav_shared.errors` | Tool-facing error text (missing file, timeout, LSP errors, …) |

## Install

As a workspace member (SpaceMaker monorepo):

```bash
uv sync --group dev
```

As a dependency of `codenav-mcp` / `webnav-mcp` it is pulled in automatically
via `tool.uv.sources` when those packages are installed from this workspace.

## License

MIT — see [LICENSE](LICENSE).

## Developed in SpaceMaker

Repo-specific agent wiring, Cursor/Claude MCP config, and deeper design notes:
[docs/agent-tooling.md](../../docs/agent-tooling.md).
