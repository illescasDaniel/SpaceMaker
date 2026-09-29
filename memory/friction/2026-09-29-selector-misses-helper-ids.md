---
date: 2026-09-29
area: webnav
severity: wrong-result
status: fixed (7c2d623)
---

**Call:** `selector("#btn-gallery-item-back")` (also reported by a Cursor agent after removing `.gallery-item-spinner`)
**Expected:** JS usage `onClick("btn-gallery-item-back", …)` in gallery.ts
**Got:** HTML/wireframe hits only — a false "nothing else references this"
**Workaround:** grep the bare name
**Idea:** false completeness is the worst failure for a "find all usages" tool; prefer over-reporting labeled low-confidence hits.
