---
name: graphify-removed-codenav-renamed
description: Graphify removed entirely; ty MCP renamed codenav; agents told to prefer it over grep
type: decision
date: 2026-09-25
status: current
supersedes: graphrag-mkdocs-graphify
superseded_by:
source:
---

Graphify removed entirely; `ty` MCP server renamed to `codenav`; AGENTS.md now instructs agents to prefer it over grep.

- **Context:** User asked for three things: (1) `AGENTS.md` should heavily instruct agents to use the custom MCP server for code navigation instead of grepping, since it's faster/simpler/more deterministic for symbol lookups; (2) Graphify (the knowledge-graph tooling adopted 2026-09-24, see the entries below) should be removed completely; (3) the MCP server, previously named `ty` in `.mcp.json`, should be renamed since `ty` is Astral's name for the type checker it wraps, not this project's server. Asked the user to pick a name (`codenav`/`pynav`/`typelens`/`symbolmap`) and the removal scope (full removal vs. strip-only) via AskUserQuestion; user picked `codenav` and full removal.
- **Decision:** Removed Graphify completely: deleted `graphify-out/` (graph.json, GRAPH_REPORT.md, memory/, reflections/, caches), deleted `.githooks/pre-commit` (its only job was regenerating Graphify's output) and the now-empty `.githooks/` directory, dropped the `graphifyy` dependency and the `graph-update`/`graph-explain`/`graph-path`/`graph-query` `taskipy` tasks from `pyproject.toml`, regenerated `uv.lock` (`uv lock` — also dropped ~30 now-unused transitive deps: `networkx`, `numpy`, `rapidfuzz`, the `tree-sitter-*` grammars), removed the `graphify-out/*` block from `.gitignore`, and stripped every Graphify reference from `AGENTS.md`, `docs/ARCHITECTURE.md` ("Developer setup"), `docs/agent-tooling.md` (advanced-usage section + Windows gotchas), `docs/index.md`, and `README.md`. Renamed `mcp-servers/ty_mcp/` → `mcp-servers/codenav_mcp/`, the `.mcp.json` server key `ty` → `codenav`, the `MCPServer(name=...)` in `server.py` from `"ty-mcp"` to `"codenav"`, and the workspace-root env var `TY_MCP_WORKSPACE` → `CODENAV_MCP_WORKSPACE` (the internal `TyLspClient` class name and `ty: ignore` type-checker comments were left untouched — those correctly refer to Astral's `ty`, not the MCP server). `AGENTS.md`'s "Orient before editing" section now names `codenav`'s tools (`search_symbol`, `definition`, `references`, `hover`, `diagnostics`) explicitly and tells agents to prefer them over grep for symbol lookups, since they resolve through real type inference rather than text matching.
- **Rationale:** Graphify's knowledge graph and `codenav`'s type-resolved navigation covered overlapping ground ("what calls what"), and the user judged `codenav` (backed by `ty`'s language server, already installed as this project's type checker) sufficient on its own — no LLM API key, no multi-second regenerate-on-commit hook, no separate `graphify-out/` artifacts to keep in sync. `AGENTS.md` previously didn't mention `codenav` at all despite it being added as an MCP server, so agents had no reason to prefer it over grep; that gap is now closed. Verified: `uv run task checks` — ruff clean, ty clean, 208 passed/6 skipped (pytest); the `web`/Biome step reported 50 warnings (0 errors), all in files untouched by this change (wireframes a11y roles, pre-existing `app.js` issues) — consistent with, not re-diffed against, the 19/50 baseline noted in the gallery-perf entry above.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-25 — Graphify removed entirely; `ty` MCP server renamed to `codenav`; AGENTS.md now instructs agents to prefer it over grep".

Also replaces: [graphify-out-diff-expected](graphify-out-diff-expected.md), [graphify-feedback-loop](graphify-feedback-loop.md).
