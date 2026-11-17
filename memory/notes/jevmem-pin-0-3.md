---
name: jevmem-pin-0-3
description: jevmem MCP pinned to >=0.3.0,<0.4 so uvx's cache cannot serve a stale release
type: decision
date: 2026-10-05
status: superseded
supersedes:
superseded_by: jevmem-db-path-userprofile
source:
---

jevmem pinned to `jevmem>=0.3.0,<0.4`.

- **Context:** the MCP configs ran `uvx --from jevmem` unpinned, so uvx's cache could keep serving an old release after a new one was published.
- **Decision:** `.mcp.json` and `.cursor/mcp.json` launch `jevmem>=0.3.0,<0.4`, the same range style as codenav.
- **Rationale:** 0.3.0 adds `JEVMEM_BASE_URL` for local decision models and the pin makes upgrades an explicit, reviewable change.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-05 — jevmem pinned to `jevmem>=0.3.0,<0.4`".

Superseded by [jevmem-db-path-userprofile](jevmem-db-path-userprofile.md).
