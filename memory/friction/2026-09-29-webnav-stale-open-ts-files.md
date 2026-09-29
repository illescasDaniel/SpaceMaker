---
date: 2026-09-29
area: webnav
severity: wrong-result
status: open
---

**Call:** append `export function probeEdit() { void apiGet("/y"); }` to `web/src/lan.ts`, then `symbol_info(name="apiGet")` / `search_symbol("probeEdit")`.
**Expected:** new reference in lan.ts; `probeEdit` found.
**Got:** neither — every `web/src` file is eagerly `didOpen`ed at startup, and tsserver ignores disk for open documents, so edits to existing files stay invisible until a positional tool/`outline` touches that exact file. (New and deleted files *are* picked up: tsserver watches disk for files it doesn't have open.)
**Workaround:** `outline(file_path=…)` the edited file first; otherwise grep.
**Idea:** same fix as `2026-09-29-codenav-stale-after-disk-edits.md` — re-stat all open files on each call and resync the changed ones (shared `LspClient`).
