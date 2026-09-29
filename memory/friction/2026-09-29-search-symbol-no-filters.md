---
date: 2026-09-29
area: codenav
severity: confusing
status: fixed (5b0ff55)
---

**Call:** `search_symbol(query="convert")`
**Got:** 50 results (~5 KB) + "and 46 more", mostly `test_given_…` functions and fields; no way to restrict to `src/` or to Class/Function kinds.
**Workaround:** `symbol_info` with an exact name, or grep.
**Idea:** optional `kind=` and `path=` (prefix/glob) filters; rank test files after source within a tier.
