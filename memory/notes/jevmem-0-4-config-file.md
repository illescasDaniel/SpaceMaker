---
name: jevmem-0-4-config-file
description: jevmem settings moved to ~/.jevmem/config.jsonc, no env in MCP configs; per-project default scope
type: decision
date: 2026-10-06
status: superseded
supersedes: jevmem-db-path-userprofile
superseded_by: memory-1-replaces-memory-bank-jevmem
source:
---

jevmem 0.4.0: settings in `~/.jevmem/config.jsonc`, per-project default scope.

- **Context:** keys and paths in `.mcp.json` risk being committed, and `${userHome}` expands to `/c:/Users/...` in Cursor on Windows (WinError 123), so the 0.3.1 env-var approach did not work in both editors.
- **Decision:** both MCP configs drop the env block and pin `jevmem>=0.4.0,<0.5`; DB path and API key come from `~/.jevmem/config.jsonc` (`~` expands on every OS). Notes default to `project:<repo name>`; `scope="global"` is explicit and recall always includes global. Supersedes the `${USERPROFILE}`/`${userHome}` decision below.
- **Rationale:** one per-user file works in every editor and keeps secrets out of the repo. `.env` was dropped to avoid two places for the key.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-06 — jevmem 0.4.0: settings in `~/.jevmem/config.jsonc`, per-project default scope".

Superseded by [memory-1-replaces-memory-bank-jevmem](memory-1-replaces-memory-bank-jevmem.md).
