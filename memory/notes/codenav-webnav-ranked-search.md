---
name: codenav-webnav-ranked-search
description: ranked symbol search, text errors, dead-server restart, ty root
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

codenav/webnav: ranked search, text errors, server restart, ty root.

- **Context:** Live testing: `search_symbol("get")` put the exact `get` method at result #50 of 384 (ty fuzzy search, workspace order) — one more fuzzy hit and the cap would hide it; `search_symbol("LspClient")` listed unrelated test names first. Missing file / non-JS path in webnav raised → opaque "Error executing tool". A dead language server was cached forever (every call waits 20s timeout). `ty check` failed on MCP tests (`_shared` unresolved), and codenav `references` missed test usages for the same reason.
- **Decision:** (1) `rank_workspace_symbols` (exact → ci-exact → prefix → substring → other) before capping. (2) `_shared/errors.py`: `TOOL_ERRORS` + `format_tool_error`; webnav raises `ToolInputError`. (3) `LspClient` fails pending futures on reader EOF (`LanguageServerExitedError`) and exposes `is_alive`; servers recreate dead clients. (4) ty `root` += `./mcp-servers`; integration test imports `codenav_mcp.ty_command`.
- **Rationale:** Agents chain search → hover; ranking keeps the intended symbol visible. Actionable text beats opaque failures. Self-healing avoids needing an MCP reload after an LSP crash. Clean ty gate and complete references for MCP code.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — codenav/webnav: ranked search, text errors, server restart, ty root".
