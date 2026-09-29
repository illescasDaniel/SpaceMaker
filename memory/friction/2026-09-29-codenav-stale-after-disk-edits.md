---
date: 2026-09-29
area: codenav
severity: wrong-result
status: open
---

**Call:** `callers(name="convert_control_flags")` after (a) creating a new `src/…/_probe.py` that calls it, (b) appending a call to an existing, not-yet-opened `application/reset_library.py`, (c) reverting/deleting those edits.
**Expected:** results track the files on disk.
**Got:** (a)/(b) new call sites invisible (also to `search_symbol`) until that exact file is touched by a positional tool/`outline`; (c) ghost callers persist after `git checkout`/`rm` (`_probe_three … calls at L36` in a now 31-line file). `symbol_info` on a symbol from a deleted file answers "File not found".
**Workaround:** `outline(file_path=…)` the edited file to force a `didChange`; otherwise grep. A server restart clears it.
**Idea:** root cause in `mcp_nav_shared/lsp_client.py`: the client never advertises `workspace.didChangeWatchedFiles`, never sends it, and never `didClose`s files — ty's view of unopened files is frozen at startup and opened files only resync when requested by path. Cheapest fix: on every tool call, re-stat `_open_files` (resync changed, `didClose` missing) and send `workspace/didChangeWatchedFiles` for files under the source root whose `(mtime, size)` changed since the last call (same re-stat trick `web_index` already uses).
