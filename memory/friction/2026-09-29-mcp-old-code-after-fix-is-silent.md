---
date: 2026-09-29
area: mcp-nav-shared
severity: confusing
status: fixed (claude/mcp-followups)
---

**Call:** any tool on an MCP server started before its own code changed
**Expected:** the fix is live (or at least I am told it is not)
**Got:** old behaviour with no hint; only a restart loads new code (a stdio server can't reload itself)
**Workaround:** restart the MCP servers after every MCP change
**Fix:** `NoticeBoard` appends `[codenav] the codenav server's own code changed since it started; restart the MCP servers …` to every result while the source differs from startup
