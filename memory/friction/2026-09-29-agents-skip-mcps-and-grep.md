---
date: 2026-09-29
area: docs
severity: confusing
status: open
---

**Source:** Cursor session feedback surveys (3 chats). Two never called codenav/webnav at all and used grep + an explore subagent; one only fetched a tool schema. One tried searching for the *tools* with `gallery|blur|loading` via a dynamic-tools search and concluded they were useless.
**Got:** the "prefer codenav/webnav" guidance in AGENTS.md wasn't strong or concrete enough to change behavior; tool-discovery by keyword doesn't surface them.
**Idea:** put 2–3 copy-paste example calls (`selector`, `callers`, `symbol_info`) in AGENTS.md "Orient before editing"; make tool descriptions lead with the question they answer ("Who uses this id/class?").
