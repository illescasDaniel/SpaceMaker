_Last updated: 2026-09-28_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Photo-backup branch** — quality gates + MCP live smoke green; ready for manual app smoke + PR when satisfied. Dev-tooling side-track continues: after the 5 earlier codenav/webnav bugs were fixed and generalized (env-var config, no hardcoded SpaceMaker paths — see `decisions.md` 2026-09-28), live re-verification found one more real bug in webnav (`<script>` blocks not indexed), now also fixed.

## Next steps

- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- Mark photo-backup branch ready for review / merge when satisfied.
- Ask the user to reload the codenav/webnav MCP servers (a running MCP process has the old `web_index.py` loaded in memory even though the module rescans on every call), then re-verify live: `diagnostics(transfer.html)` → no warnings; `diagnostics(wireframes/app.html)` → only `.disconnected`/`.alert-actions`/`.ui-mode-toggle`; `selector(".slide-in-next-start")` shows a `class-var +=` JS hit.

## Just changed

- **webnav `<script>` scanning bug** (found + fixed 2026-09-28, same day as live re-verify): `_scan_html_text` scanned `<style>` but not `<script>`, so JS-only usages inside HTML files (all of `static/transfer.html`, most of `wireframes/app.html` — wireframes are self-contained HTML with inline JS) looked unreferenced. Fixed with `_SCRIPT_BLOCK_RE` + `line_offset` threaded through `_scan_js_text`/`_scan_markup_attrs` (mirrors the existing `<style>` path). Also generalized the `className =` heuristic to a class-ish local var grown with `+=` (`mediaClass += ' slide-in-next-start'`, tagged `class-var +=`), since that pattern showed up in the wireframe once script scanning existed. Verified against real repo content (not just unit tests): `transfer.html` 7→0 false warnings, `app.html` 14→6 (remaining 6 confirmed genuinely dead via grep). +6 tests (`tests/unit/test_mcp_web_index.py`, now 44); `docs/agent-tooling.md` updated; `uv run task checks` green (382 tests).
- Earlier this session: fixed all 5 codenav/webnav live-smoke bugs from `progress.md`, and generalized both servers per explicit user request ("I might want to release them as separate independent tools for other projects... let's not hard-code too much of our spacemaker repository structure into them"): new `CODENAV_MCP_SOURCE_ROOT` / `WEBNAV_MCP_ROOTS` env vars replace hardcoded `src`/`static`/`wireframes` constants; added `format_references()`, fixed `_exact_candidates` case-exact preference, JS-string `class=`/`id=` scanning, dynamic-prefix-as-reference logic.
- Pushed via `/save-changes` (2026-09-28). New side-track starting: user wants the codenav/webnav MCP test files (`tests/unit/test_mcp_nav_format.py`, `tests/unit/test_mcp_web_index.py`, `tests/integration/test_mcp_ty_search_smoke.py`) moved under `mcp-servers/` so each server can be bundled standalone — still need to figure out the right layout (per-server `tests/` dirs vs. shared) and update `pyproject`/`checks.sh` test discovery paths accordingly.
