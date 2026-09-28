_Last updated: 2026-09-28_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Photo-backup branch** — quality gates + MCP live smoke green; ready for manual app smoke + PR when satisfied. Also just finished a dev-tooling side-track: codenav/webnav intent-level tools + workspace-wide CSS index (see `decisions.md` 2026-09-28).

## Next steps

- Manual app checks still open: Clear prefs list width; Compress-off upload → Gallery; sticky header.
- Mark photo-backup branch ready for review / merge when satisfied.
- Fix MCP bugs found in live smoke (see `progress.md` → *codenav/webnav live-smoke bugs*).

## Just changed

- Live-smoked the reloaded codenav/webnav tools (2026-09-28): all new tools respond correctly; 4 bugs + 1 verbosity nit logged in `progress.md`.
- Implemented the approved plan (`docs/agent-tooling.md` now reflects all of it): multi-line diagnostic formatting fix; codenav `symbol_info`/`outline`/`callers`/`implementations` + `_shared/resolve.py`; webnav `web_index.py` (CSS var / `#id`/`.class` cross-file index) + `css_var`/`selector` tools + `references`/`definition`/`diagnostics` enrichment for `.css`/`.html`.
- Added `tests/unit/test_mcp_web_index.py` (25 tests). Full `uv run pytest` green (357 passed); `ruff check`/`ty check` clean on `mcp-servers/` and the new test file.
- Verified MCP (codenav/webnav) live: ranking, name-column hover chain, references into tests/`mcp-servers`, clear missing-file / unsupported-ext errors.
- Confirmed MCP unit + integration tests already run via `scripts/quality/pytest.sh` → `uv run task checks` (no checks.sh change needed).
