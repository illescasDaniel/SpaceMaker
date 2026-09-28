_Last updated: 2026-09-28_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Photo-backup branch** — quality gates + MCP live smoke green; ready for manual app smoke + PR when satisfied. Just finished a dev-tooling side-track: fixed the 5 codenav/webnav bugs found in live smoke, and generalized both servers (env-var config, no hardcoded SpaceMaker paths) since the user may release them as standalone tools for other projects (see `decisions.md` 2026-09-28).

## Next steps

- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- Mark photo-backup branch ready for review / merge when satisfied.
- Ask the user to reload the codenav/webnav MCP servers, then re-verify the 5 fixed bugs live (`implementations("WebSocketLike")` no self-match, `implementations("AppServices")` → not-a-Protocol message, `callers("repo_root")` unambiguous, webnav `diagnostics(index.html)` only flags `.thumb-removing`/`.ui-mode-toggle`, `selector("#view-components")` shows the dynamic match, `references` on `showView` is compact).

## Just changed

- Fixed all 5 codenav/webnav live-smoke bugs from `progress.md`, and generalized both servers per explicit user request ("I might want to release them as separate independent tools for other projects... let's not hard-code too much of our spacemaker repository structure into them"): new `CODENAV_MCP_SOURCE_ROOT` / `WEBNAV_MCP_ROOTS` env vars (same override-with-default shape as the existing `*_MCP_WORKSPACE` vars) replace hardcoded `src`/`static`/`wireframes` constants in `mcp-servers/codenav_mcp/server.py` and `mcp-servers/webnav_mcp/{server.py,web_index.py}`; SpaceMaker's specific values now live only in `.mcp.json`/`.cursor/mcp.json`.
- Added `format_references()` (`_shared/format.py`) for a compact `references` output above 8 hits; used by both servers.
- Fixed `_exact_candidates` (`_shared/resolve.py`) to prefer case-exact matches.
- `web_index.py`: JS-string `class=`/`id=` markup scanning, `className`/`classList` string-concatenation dynamic-prefix tagging, dynamic-prefix hits now count as references (suppress unreferenced warnings) and are surfaced in `selector()` as partial matches.
- Updated `docs/agent-tooling.md` (env vars, `implementations`'s Protocol-only + self-exclusion behavior, exact-case-match preference, JS-string scanning, corrected dynamic-prefix behavior, `references` compact threshold) and fixed a stale `src/spacemaker/domain/ports/application` path in `AGENTS.md`.
- Added ~24 new tests across `tests/unit/test_mcp_web_index.py` and `tests/unit/test_mcp_nav_format.py` (now 34 and 40+ tests respectively); `uv run task checks` green (378 tests passing).
- Not yet done: commit + push this work, then ask the user to reload the MCP servers for live re-verification (see Next steps).
