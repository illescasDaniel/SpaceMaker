---
date: 2026-09-29
area: mcp-nav-shared
severity: slow
status: open
---

**Call:** any codenav tool, warm (measured with a stdio client on this repo).
**Before/after the freshness fix:** ~3–10 ms → ~22–28 ms. The cost is `LspClient.refresh()` walking the workspace (`os.walk` + `stat` of every `.py`) on every call.
**Impact:** negligible for a human-paced agent; noticeable only in tight loops.
**Idea:** scope the walk to the source root(s) + tests instead of the whole workspace, or reuse the walk between calls within a ~50 ms window / use inotify (watchfiles) where available.
