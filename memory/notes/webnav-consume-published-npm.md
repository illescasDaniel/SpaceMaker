---
name: webnav-consume-published-npm
description: configs launch the published webnav-ts-mcp (^0.1.0) instead of a local checkout
type: decision
date: 2026-09-30
status: superseded
supersedes: webnav-ts-own-repo
superseded_by: webnav-ts-mcp-0-2-write-queue
source:
---

SpaceMaker consumes the published `webnav-ts-mcp`; Python `webnav-mcp` 0.1.2.

- **Context:** `webnav-ts-mcp` 0.1.0 is on npm (https://www.npmjs.com/package/webnav-ts-mcp) and on GitHub (`illescasDaniel/webnav-ts-mcp`, tag `v0.1.0`). The Python `webnav-mcp` had an uncommitted `outline` fix.
- **Decision:** (1) `.mcp.json` / `.cursor/mcp.json` launch `npx --yes webnav-ts-mcp@^0.1.0` instead of the local checkout's launcher. (2) Python `webnav-mcp` 0.1.2 (outline hides imports) committed, pushed, tagged `v0.1.2`, uploaded to PyPI and verified with `task test-package`. (3) `webnav-ts-mcp` gained `npm run upload` (`scripts/publish.sh`) and `npm run test-package`, mirroring the Python tasks.
- **Trade-off:** first start downloads ~180 MB into npm's cache; `^0.1.0` picks up patch releases automatically.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — SpaceMaker consumes the published `webnav-ts-mcp`; Python `webnav-mcp` 0.1.2".

Superseded by [webnav-ts-mcp-0-2-write-queue](webnav-ts-mcp-0-2-write-queue.md).
