# codenav and webnav MCP servers
Updated: 2026-11-17. The code-navigation MCP servers agents use here, how they were built and where they live now.

## Now
Both servers live in their own repos and are consumed as published packages: codenav from PyPI ([mcp-packages-separate-repos](../notes/mcp-packages-separate-repos.md)), webnav as `webnav-ts-mcp@^0.2.0` on npm ([webnav-ts-mcp-0-2-write-queue](../notes/webnav-ts-mcp-0-2-write-queue.md)). They pick the workspace per request for worktrees ([mcp-workspace-per-request](../notes/mcp-workspace-per-request.md)) and key caches on file stat ([mcp-caches-keyed-on-stat](../notes/mcp-caches-keyed-on-stat.md)). Tool bugs found while using them are in `memory/friction/`.

## How it got here
- 2026-09-25 webnav created next to the ty MCP (renamed codenav) ([note](../notes/webnav-mcp-server-created.md)).
- 2026-09-28 in-repo uv workspace of three packages, extracted to separate repos on 2026-09-30 ([note](../notes/mcp-packages-separate-repos.md)).
- 2026-09-30 webnav ported to TypeScript: experiments/ prototype → self-building launcher → own repo → npm ^0.1 → ^0.2 on 2026-10-05 ([note](../notes/webnav-ts-mcp-0-2-write-queue.md)).
- 2026-09-30 TypeScript 7 native tsc LSP replaced the typescript@5 npx fallback ([note](../notes/typescript-7-native-tsc-lsp.md)).

## Notes
- [webnav pinned to `webnav-ts-mcp@^0.2.0` (write tools + write queue)](../notes/webnav-ts-mcp-0-2-write-queue.md) 2026-10-05: webnav-ts-mcp ^0.2.0 serializes write tools; a local ~/.claude.json override had shadowed .mcp.json
- [MCP packages extracted into separate repos](../notes/mcp-packages-separate-repos.md) 2026-09-30: codenav-mcp, webnav-mcp and mcp-nav-shared live in their own repos; SpaceMaker uses the PyPI releases
- [TypeScript 7 CLI + webnav native `tsc` LSP](../notes/typescript-7-native-tsc-lsp.md) 2026-09-30: web tooling on TypeScript 7; webnav launches tsc --lsp --stdio instead of typescript-language-server
- [MCP packages: how they're published](../notes/mcp-packages-publishing.md) 2026-09-30: console scripts and documented uvx install; ty lookup order; SpaceMaker ran the editable source
- [MCP follow-up review fixes](../notes/mcp-follow-up-review-fixes.md) 2026-09-29: best-effort hover enrichment, clean restart/stop, config change detected by content sha256
- [MCP: restart on config change, warn on stale code, richer hover, position validation](../notes/mcp-restart-on-config-change.md) 2026-09-29: MCP servers restart on config change and warn while running stale code; richer hover; position checks
- [MCP refresh walk skips nested checkouts; probe document at the workspace root](../notes/mcp-refresh-skips-nested-checkouts.md) 2026-09-29: refresh walk prunes nested .git dirs; probe document at the workspace root
- [MCP servers pick the workspace per request (worktree support)](../notes/mcp-workspace-per-request.md) 2026-09-29: Claude Code starts MCP servers once from the main checkout, so servers pick the workspace per request
- [MCP trial: param aliases, webnav composites, quieter search_symbol](../notes/mcp-param-aliases-composites.md) 2026-09-29: name/query aliases on all name tools, webnav composites, quieter search_symbol
- [webnav `selector`: treat exact-name JS string literals as references](../notes/webnav-selector-string-literals.md) 2026-09-29: webnav selector counts exact-name JS string literals as references
- [MCP caching: key everything on file stat/version, never on time; add TypeScript to webnav](../notes/mcp-caches-keyed-on-stat.md) 2026-09-29: all MCP caches validated by (mtime_ns, size) on every call, never by time; TypeScript added to webnav
- [webnav: prefer npm `.cmd` shims on Windows](../notes/webnav-windows-cmd-shims.md) 2026-09-28: webnav prefers npm .cmd shims on Windows
- [Standalone MCP packages ship README + MIT LICENSE](../notes/mcp-packages-readme-license.md) 2026-09-28: standalone MCP packages ship README and MIT LICENSE
- [Align `mcp-nav-shared` import name with distribution name](../notes/mcp-nav-shared-import-name.md) 2026-09-28: shared package import name aligned to mcp_nav_shared
- [codenav/webnav: fix live-smoke bugs, generalize for standalone reuse](../notes/codenav-webnav-live-smoke-fixes.md) 2026-09-28: implementations excludes the port and Protocols; generalized for standalone reuse
- [codenav/webnav: intent-level tools, workspace-wide CSS index, multi-line diagnostics](../notes/codenav-webnav-intent-tools.md) 2026-09-28: name-based composites symbol_info/outline/callers/implementations; workspace-wide CSS index
- [codenav/webnav: ranked search, text errors, server restart, ty root](../notes/codenav-webnav-ranked-search.md) 2026-09-28: ranked symbol search, text errors, dead-server restart, ty root
- [search_symbol: walk past decorator lines for name column](../notes/search-symbol-decorator-lines.md) 2026-09-27: search_symbol walks past decorator lines to the name column
- [search_symbol: name columns, kind labels, result cap, live ty smoke](../notes/search-symbol-name-columns.md) 2026-09-27: search_symbol name columns, kind labels, 50-result cap, live ty smoke
- [Harden codenav/webnav: character columns, path:line:col, LSP errors, diag fallback](../notes/codenav-webnav-hardening.md) 2026-09-27: UTF-16 character columns, path:line:col, LSP error text, diagnostics fallback
- [New `webnav` MCP server (JS/HTML/CSS nav); shared `_shared/lsp_client.py`; fixed cold `search_symbol` returning no matches](../notes/webnav-mcp-server-created.md) 2026-09-25: webnav MCP for JS/HTML/CSS with a shared LSP client; eager-open fixes cold search

## History (superseded)
- [SpaceMaker consumes the published `webnav-ts-mcp`; Python `webnav-mcp` 0.1.2](../notes/webnav-consume-published-npm.md) 2026-09-30 → superseded by webnav-ts-mcp-0-2-write-queue
- [webnav TS port extracted to its own repo `webnav-ts-mcp`](../notes/webnav-ts-own-repo.md) 2026-09-30 → superseded by webnav-consume-published-npm
- [webnav TS launcher self-builds; `outline` hides imports](../notes/webnav-ts-launcher-self-builds.md) 2026-09-30 → superseded by webnav-ts-own-repo
- [SpaceMaker's webnav MCP now runs the TypeScript port; inherited lookup, `callers`, `implementations`](../notes/webnav-runs-typescript-port.md) 2026-09-30 → superseded by webnav-ts-launcher-self-builds
- [Prototype: TypeScript port of webnav-mcp (`experiments/webnav-mcp-ts/`)](../notes/webnav-typescript-port-prototype.md) 2026-09-30 → superseded by webnav-runs-typescript-port
- [webnav's npx `typescript-language-server` fallback must pin and bundle `typescript@5`](../notes/webnav-npx-pin-typescript-5.md) 2026-09-28 → superseded by typescript-7-native-tsc-lsp
- [Rename shared MCP folder `_shared` → `mcp-nav-shared`](../notes/mcp-nav-shared-folder-rename.md) 2026-09-28 → superseded by mcp-nav-shared-import-name
- [mcp-servers: turn `_shared`/`codenav_mcp`/`webnav_mcp` into a uv workspace of three installable packages](../notes/mcp-servers-uv-workspace.md) 2026-09-28 → superseded by mcp-packages-separate-repos
