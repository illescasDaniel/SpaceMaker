---
date: 2026-09-29
area: mcp-nav-shared
severity: confusing
status: fixed (claude/mcp-followups)
---

**Call:** any codenav/webnav call after editing `pyproject.toml` (ty) or `tsconfig.json` (tsserver)
**Expected:** answers follow the new config
**Got:** the language server had read its config at startup, so answers used the old one until the MCP server was restarted by hand
**Workaround:** restart the MCP servers
**Fix:** `LspClient.config_names` + `restart()` from `refresh()`; the next result says `restarted the language server because <file> changed`
