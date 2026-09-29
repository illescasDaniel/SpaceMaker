---
date: 2026-09-29
area: webnav
severity: confusing
status: fixed (7c2d623)
---

**Call:** `webnav.search_symbol("gallery")`
**Expected:** functions/interfaces first
**Got:** the 50-result cap filled with repeated `S.galleryHasMore = …` Property symbols
**Workaround:** narrower query / grep
**Idea:** rank Property/Field after declarations (done). Consider also deduping identical name+kind hits per file.
