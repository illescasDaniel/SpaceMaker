---
date: 2026-09-29
area: codenav
severity: wrong-result
status: fixed (7c2d623)
---

**Call:** `symbol_info("AppServices.start_convert")` / `callers(...)`
**Expected:** `JobsMixin.start_convert` (AppServices is composed from mixins)
**Got:** "No symbol found"
**Workaround:** query the bare name `start_convert`
**Idea:** dotted lookup must follow inheritance (now via typeHierarchy/supertypes).
