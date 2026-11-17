---
name: mcp-caches-keyed-on-stat
description: all MCP caches validated by (mtime_ns, size) on every call, never by time; TypeScript added to webnav
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

MCP caching: key everything on file stat/version, never on time; add TypeScript to webnav.

- **Context:** User asked whether an in-memory cache with automatic invalidation would speed up the codenav/webnav tools. Measured first: most tools were already ≤ a few ms warm (ty/tsserver keep their own indexes; `ensure_open` already syncs by mtime/size). The real warm costs were `implementations` (~140 ms: per-file `ast.parse`+`ast.walk` in `_protocol_class_names` was ~70%, not the type-check probes), and webnav `css_var`/`selector`/HTML+CSS `diagnostics` (~60–115 ms: full re-scan of the roots per call, contradicting the old "a few ms" docstring). Separately found webnav rejected `.ts` although `web/src/*.ts` is now the authoritative source, and that tsserver-backed `diagnostics` silently returned nothing on the first call (no pull support; push not awaited). User ranked TS support first, then index cache, then `implementations` probes, then diagnostics timing.
- **Decision:** (1) webnav routes `.ts/.mts/.cts` to the existing typescript-language-server with a per-suffix languageId. (2) All caches are validated on every call by `(mtime_ns, size)` (or the document version `ensure_open` derives from it) — no TTLs, no file watchers. (3) `implementations` probe verdicts can depend on transitive imports, so they are keyed to one signature of every file under `CODENAV_MCP_SOURCE_ROOT` and dropped wholesale on any change (correct over granular). (4) Push-only diagnostics: wait (≤5 s) for the first `publishDiagnostics` after the last sync.
- **Follow-up (same day):** compiled `static/js/*.js` is now excluded from webnav navigation via new `WEBNAV_MCP_EXCLUDE` (set in `.mcp.json`/`.cursor/mcp.json`; also dropped from `jsconfig.json` `include`) — TS is the source of truth, we don't handle transpilation. The index still scans it (root usage data, not navigation). The codenav probe-cache signature now also covers `pyproject.toml`, `uv.lock` and `.venv/**/site-packages` mtime, so `uv sync` invalidates automatically (a sync-dev hook can't reach the separate MCP server process). Live tsserver smoke tests added in `webnav_mcp/tests/test_ts_smoke.py`.
- **Rationale:** Stat-keyed caches keep "automatic invalidation" trivially correct and cheap (the directory walk/stat stays; only parsing/probing is skipped). Not caching LSP results (hover/references/…) — ty/tsserver already do it. Package changes are covered by the environment signature above.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — MCP caching: key everything on file stat/version, never on time; add TypeScript to webnav".
