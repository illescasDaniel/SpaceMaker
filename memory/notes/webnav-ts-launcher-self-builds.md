---
name: webnav-ts-launcher-self-builds
description: launcher ran npm ci / build when dist/ was missing or stale; outline hides imports
type: decision
date: 2026-09-30
status: superseded
supersedes: webnav-runs-typescript-port
superseded_by: webnav-ts-own-repo
source:
---

webnav TS launcher self-builds; `outline` hides imports.

- **Context:** A fresh clone/worktree without `dist/` made the host drop webnav for the whole session (`CONNECTION_CLOSED`). Separately, TypeScript's LSP reports imported names as top-level `Variable`s, which filled the top of every `outline`.
- **Decision:** (1) `.mcp.json` / `.cursor/mcp.json` now run `experiments/webnav-mcp-ts/bin/launch.mjs`: it runs `npm ci` / `npm run build` (output to stderr, stdout is the protocol) when `node_modules` is missing or `src/` is newer than `dist/`, then imports `dist/cli.js`. `setup:webnav` stays as an optional pre-build. (2) `outline` (default, not `detailed`) drops symbols declared on `import` statement lines, found in the source text so multi-line imports work; same fix in the Python `webnav-mcp` (kept out of `mcp-nav-shared`, since codenav's Python imports aren't affected). (3) Root `biome.json` force-ignores `!!**/experiments` (nested `root: true` config otherwise fails the web gate).
- **Rationale / trade-off:** the first start takes ~a minute (npm ci) and may hit a host connection timeout; later starts add only a source-mtime scan (~ms).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — webnav TS launcher self-builds; `outline` hides imports".

Superseded by [webnav-ts-own-repo](webnav-ts-own-repo.md).
