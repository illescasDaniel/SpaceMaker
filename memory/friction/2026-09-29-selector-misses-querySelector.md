---
date: 2026-09-29
area: webnav
severity: wrong-result
status: fixed (7c2d623)
---

**Call:** `selector(".gallery-item-media")`
**Expected:** JS hit for `stage.querySelector(".gallery-item-media")` (gallery-item.ts:34)
**Got:** only the `className =` hit; regex `querySelectorAll?\(` never matched plain `querySelector(`
**Workaround:** grep
**Idea:** every regex in the index needs a positive test per API it claims to cover.
