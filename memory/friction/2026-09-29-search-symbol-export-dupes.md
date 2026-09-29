---
date: 2026-09-29
area: webnav
severity: confusing
status: fixed (this branch)
---

**Call:** `webnav.search_symbol("gallery")` (re-check after Property ranking fix)
**Expected:** declarations first; at most one Property hit per file; no export-list Variable twin
**Got:** still many duplicate `galleryHasMore` Property lines + `Function`+`Variable` for the same export; `… and 79 more`
**Workaround:** narrower query
**Idea:** dedupe `(name, kind, file)`; drop Variable when a declaration exists in the same file
