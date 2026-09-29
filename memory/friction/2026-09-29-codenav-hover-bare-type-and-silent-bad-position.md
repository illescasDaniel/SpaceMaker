---
date: 2026-09-29
area: codenav
severity: confusing
status: fixed (claude/mcp-followups)
---

**Call:** `hover(routes/convert.py, 19, 9)` on `services`; `hover(routes/convert.py, 500, 1)`
**Expected:** where `AppServices` lives; a range error for line 500
**Got:** `AppServices` and nothing else; "No hover information at that position." for a line past the end
**Workaround:** `definition`, then read the file
**Fix:** bare type hovers append the `typeDefinition` location, header and first docstring line; `InvalidPositionError` for lines/columns outside the file (all position tools, both servers)
