---
date: 2026-10-03
area: tooling
severity: wrong-result
status: fixed (uncommitted in Jev-things: check_same_thread=False + per-call lock in mcp_server.py, tests/test_mcp_server.py)
---

**Call:** `memory_pin(node_id=42)` (jevmem MCP, trial wiring)
**Expected:** `{"ok": true}`
**Got:** bare "Error executing tool memory_pin". Root cause: `ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. The MCP framework runs sync tools on worker threads, and the store connection was bound to whichever thread first opened it. Any jevmem tool could fail; `memory_list` only worked because it happened to land on the same thread.
**Workaround:** `uv run jevmem pin <id>` from the CLI.
**Idea:** the MCP server should surface the exception text instead of a bare "Error executing tool".
