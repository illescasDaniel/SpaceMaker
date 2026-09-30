---
date: 2026-09-30
area: webnav
severity: confusing
status: fixed (outline hides import statements unless detailed=true; TS port + Python webnav-mcp)
---

**Call:** `outline(file_path="web/src/gallery-item.ts")`
**Expected:** the file's own functions/classes
**Got:** a dozen `[Variable]` rows (`apiSend`, `showView`, `GalleryItem`, ...) that are just imports, before any real symbol
**Workaround:** skim past them
**Idea:** (done) detect import statements from source text and drop their symbols in the default view
