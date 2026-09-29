---
date: 2026-09-29
area: webnav
severity: confusing
status: open
---

**Call:** `outline(file_path="web/src/api.ts")`, `outline(file_path="web/src/gallery-item.ts")`
**Expected:** like codenav's outline — top-level declarations in source order.
**Got:** alphabetical order (`apiGet :25` before `apiSend :6`), plus every local const, object-literal key (`Accept`, `method`, `once`) and anonymous callback; ~4 KB for a 520-line file, hard to scan.
**Workaround:** read the file.
**Idea:** sort by start line, and drop Property/Constant/Variable children below function level by default (a `depth`/`detailed` flag can bring them back).
