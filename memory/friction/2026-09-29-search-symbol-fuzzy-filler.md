---
date: 2026-09-29
area: codenav
severity: confusing
status: fixed (search_symbol fuzzy=, claude/mcp-evaluation-report)
---

**Call:** `search_symbol(query="_probe")`
**Expected:** the handful of symbols whose name contains `_probe`.
**Got:** those first (ranking works), then 60+ fuzzy subsequence matches from ty up to the 50 cap, e.g. `test_given_lan_host_when_spa_entry_for_gallery_then_mobile_gallery`, ending "… and 21 more". Reads as if all 71 matched.
**Workaround:** add `kind=`/`path=`, or use `symbol_info` with an exact name.
**Idea:** when tiers 0–3 (exact/prefix/substring) have hits, list only those and summarise the rest as "N more fuzzy matches (pass fuzzy=true)"; keep fuzzy hits when nothing else matches (useful for abbreviations like `LspCl`).
