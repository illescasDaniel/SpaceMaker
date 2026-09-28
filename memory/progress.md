# Progress

Open items only. Finished work: `memory/archive.md`.

## SpaceMaker app

- [x] **Photo backup compress preference** — Full SDD (wireframe → spec → architecture → tests → impl) approved in chat 2026-09-26. Compress media checkbox, persistence, tools gate, Easy auto-convert gating.
- [x] **Promote uncompressed + processed/ + Settings chrome** — Full SDD 2026-09-27. Compress-off promotes originals→`processed/`; rename `converted/`→`processed/` (+ migration); sticky Home|Gallery|Settings; clear prefs / reset library / legal / tools; window 1152×864. Awaiting manual smoke + PR.
- [x] **Gallery orphan cache cleanup** — injective path-mirrored thumbs/exports;
  in-app delete + sync GC for index/thumbs/exports; SPEC + arch approved;
  merged via PR #4 (`1e516d0` on `main`)
- [x] **codenav/webnav MCP harden** — character-offset docs, `path:line:col` headers, LSP error surfacing, diagnostics push fallback, shared formatters, unit tests (plan approved 2026-09-27)
- [x] **codenav/webnav search_symbol polish** — name-column (not keyword), SymbolKind labels, result cap 50, skippable live ty smoke, HTML/CSS search documented as unsupported (2026-09-27)
- [x] **codenav/webnav decorator name columns** — `_name_position` walks range + lookahead past `@…` so decorated class search→hover works (2026-09-27)
- [x] **codenav/webnav live-test fixes** — ranked search before cap, text errors (missing file/unsupported/timeout/exited), dead-server restart, ty root `mcp-servers` (2026-09-28)
- [x] **webnav: inline `<script>` blocks not indexed** (found 2026-09-28 in live re-verify, fixed same day) — `_scan_html_text` scanned `<style>` but not `<script>`, so JS usages inside HTML files were invisible to `selector`/`diagnostics`. Fixed: `_SCRIPT_BLOCK_RE` (skips `src=`) + `_scan_js_text`/`_scan_markup_attrs` now take a `line_offset` (mirroring the `<style>` path). Confirmed against the real repo: `static/transfer.html`'s 7 false "never referenced" warnings are gone; `wireframes/app.html` dropped from 14 to 6 (the remaining 6 — `.disconnected`, `.alert-actions`, `.ui-mode-toggle` — are genuinely dead, verified by grep). Also generalized the `className =` heuristic to a class-ish local var grown with `+=` (`mediaClass += ' slide-in-next-start'`), tagged `class-var +=`; narrowed with a `className`-literal exclusion so the two regexes don't double-count. +6 tests in `tests/unit/test_mcp_web_index.py` (44 now); `uv run task checks` green (382 tests). Docs updated (`docs/agent-tooling.md`). Not yet done: ask the user to reload webnav MCP for live re-verification (rescans-on-call means only the running process's loaded module is stale).
- [x] **codenav/webnav live-smoke bugs** (found 2026-09-28, fixed same day)
  - codenav `implementations`: excludes the queried class + any candidate that is itself a `Protocol`; rejects non-`Protocol` `port_name` with an explanatory message instead of self-matching.
  - codenav name resolution: `_exact_candidates` now prefers a case-exact match over a case-insensitive one, so `callers("repo_root")` no longer ties with `REPO_ROOT`.
  - webnav `diagnostics`: scans `class="…"`/`id="…"` inside JS string literals (fixes `.gallery-loading-spinner` false "never referenced"); `className`/`classList` string-concatenation now tags the trailing token as a dynamic prefix, and a dynamic-prefix hit suppresses the unreferenced warning for any longer token it's a prefix of (fixes `.resolution-*`).
  - webnav `selector("#view-components")` now surfaces the `"view-" + resolved` dynamic hit as a "dynamic partial match via '#view-'" alongside exact hits.
  - webnav (and codenav) `references` now uses a shared `format_references()`: full snippets at/under 8 hits, compact `L<line>:<col>` grouped-by-file list above that.
  - Also generalized both servers for potential standalone release (user request): `CODENAV_MCP_SOURCE_ROOT` and `WEBNAV_MCP_ROOTS` env vars replace what used to be hardcoded `src`/`static`/`wireframes` paths; SpaceMaker's own values now live only in `.mcp.json`/`.cursor/mcp.json`. See `decisions.md` 2026-09-28.
- [x] **codenav/webnav: intent-level tools + workspace CSS index** — multi-line diagnostic formatting fix; codenav `symbol_info`/`outline`/`callers`/`implementations` (name-based, `_shared/resolve.py`, type-verified `Protocol` conformance probe); webnav `web_index.py` cross-file `--custom-property`/`#id`/`.class` scanner + `css_var`/`selector` tools + `references`/`definition`/`diagnostics` enrichment; docs + `tests/unit/test_mcp_web_index.py` (25 tests); full `uv run pytest` green (357 passed) (2026-09-28)
- [x] **Gate fixes (ruff/ty)** — import sort + unused `Path`; keep FastAPI `app` ref for `app.state.services` monkeypatch (2026-09-28)
- [x] **Biome warnings** — remove unused `lastMainView`; Settings confirm `div role=group` → `fieldset` (app + wireframe) (2026-09-28)
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
