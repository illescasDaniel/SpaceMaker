---
date: 2026-09-29
area: webnav
severity: missing-feature
status: fixed (this branch)
---

**Call:** (mental model) `webnav.symbol_info` / `webnav.outline`
**Expected:** same one-call composites as codenav for JS/TS
**Got:** only `search_symbol` → chain hover/definition/references, or Read the whole file
**Workaround:** Read / Grep
**Idea:** add `symbol_info` + `outline` on the TS client (done)
