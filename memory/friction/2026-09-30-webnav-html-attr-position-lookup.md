---
date: 2026-09-30
area: webnav
severity: wrong-result
status: fixed (branch claude/mcp-tools-pypi-review-727d33)
---

**Call:** `references(file_path="web/index.html", line=1, column=<inside "card" of class="card">)`
**Expected:** `.card` hits from the cross-file index (CSS rule + class attribute)
**Got:** `No references found at that position.` `token_at_position` only knew CSS-syntax tokens (`.card`, `#main`), which markup never spells, so the lookup fell through to the HTML language server.
**Workaround:** `selector(name=".card")`
**Idea:** done: a cursor on a word inside an `id="..."`/`class="..."` value maps to `#name`/`.name`.
