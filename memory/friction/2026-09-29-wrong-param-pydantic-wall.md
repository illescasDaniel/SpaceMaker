---
date: 2026-09-29
area: mcp-nav-shared
severity: confusing
status: fixed (this branch)
---

**Call:** `symbol_info(query="JobsMixin.start_convert")` / `search_symbol(name="gallery")`
**Expected:** soft ToolInputError hint, or accept the alias
**Got:** opaque pydantic `Field required` wall; agents abandoned MCP for grep
**Workaround:** re-fetch schema and guess the other param name
**Idea:** shared `resolve_name_query`; optional params on all name-based tools
