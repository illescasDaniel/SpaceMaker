---
name: mcp-param-aliases-composites
description: name/query aliases on all name tools, webnav composites, quieter search_symbol
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

MCP trial: param aliases, webnav composites, quieter search_symbol.

- **Context:** Live trial found happy paths solid, but agents still abandoned MCPs after one wrong param (`query` vs `name` → pydantic wall), webnav lacked `symbol_info`/`outline` (forced Read/grep chains), and `search_symbol("gallery")` still flooded the 50-cap with duplicate Property hits plus export-list Variable twins. After ship, `symbol_info` was still ambiguous on Function + `export { foo }` Variable.
- **Decision:** Shared `mcp_nav_shared.params.resolve_name_query` on all name-based tools (optional params + soft ToolInputError). webnav gained `symbol_info`/`outline` via the same `resolve_symbol` path as codenav (JS/TS only). `filter_workspace_symbols` collapses repeated Property/Field hits per file and drops same-file Variables when a declaration kind exists; `resolve_symbol` uses that filter too. Docs/AGENTS/READMEs/friction updated; no new text-search MCP (grep stays for free text).
- **Rationale:** Highest-ROI friction from the trial; aliases are cheap forgiveness; composites are why codenav feels one-call; Property-only dedupe avoids collapsing two same-named methods on different classes in one file.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — MCP trial: param aliases, webnav composites, quieter search_symbol".
