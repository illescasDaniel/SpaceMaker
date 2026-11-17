---
name: webnav-ts-mcp-0-2-write-queue
description: webnav-ts-mcp ^0.2.0 serializes write tools; a local ~/.claude.json override had shadowed .mcp.json
type: decision
date: 2026-10-05
status: current
supersedes: webnav-consume-published-npm
superseded_by:
source:
---

webnav pinned to `webnav-ts-mcp@^0.2.0` (write tools + write queue).

- **Context:** the local checkout of `webnav-ts-mcp` gained the write tools. A live concurrency test found two write-vs-write races: concurrent writes to one file were rejected as "changed since the preview", and a write running beside a multi-file rename type-checked against a half-synced state and reported phantom errors. Reads were never affected.
- **Decision:** the package serialises write tools in arrival order (published as 0.2.0, tag `v0.2.0`), and both host configs now launch `npx --yes webnav-ts-mcp@^0.2.0`. `^0.1.1` cannot resolve to 0.2.0, so the range had to change.
- **Rationale:** agents fire parallel tool calls, so queueing writes is the only way they all succeed; the published package passed the same scenarios that failed before. A local-scope `webnav` override in `~/.claude.json` shadowed `.mcp.json` and was removed.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-05 — webnav pinned to `webnav-ts-mcp@^0.2.0` (write tools + write queue)".
