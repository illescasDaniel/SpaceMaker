---
date: 2026-09-29
area: webnav
severity: confusing
status: fixed (5b0ff55)
---

**Call:** `definition(file_path=".../shell-gallery.css", line=6, column=19)` (cursor on `var(--bg)`)
**Expected:** the definition of `--bg` for that file's own root.
**Got:** the full `css_var` dump — definitions *and* usages, for every root including wireframes (~1.7 KB).
**Workaround:** read only the first section.
**Idea:** scope position queries to the file's own root; `definition` → definitions only, `references` → that root's defs + usages; fall back to all roots (with a note) when the own root has nothing.
