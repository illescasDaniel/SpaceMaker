---
name: jevmem-db-path-userprofile
description: ${HOME} is unset in Claude Code on Windows, so DB path used USERPROFILE / userHome; pin 0.3.1
type: decision
date: 2026-10-06
status: superseded
supersedes: jevmem-pin-0-3
superseded_by: jevmem-0-4-config-file
source:
---

jevmem DB path via `${USERPROFILE}` / `${userHome}`, pin 0.3.1.

- **Context:** testing jevmem on Windows, `JEVMEM_DB=${HOME}/.jevmem/spacemaker.db` in `.mcp.json` was not expanded (`HOME` is unset in Claude Code's Windows environment), so the server silently created a literal `${HOME}/` directory in the repo and used an empty DB.
- **Decision:** `.mcp.json` uses `${USERPROFILE}/.jevmem/spacemaker.db`; `.cursor/mcp.json` uses Cursor's `${userHome}`; both pin `jevmem>=0.3.1,<0.4`. jevmem 0.3.1 raises on a `JEVMEM_DB` containing `${`.
- **Rationale:** `USERPROFILE` is always set on Windows, and the guard turns this silent failure into a clear error. Rejected: keeping `${HOME}` (works only under bash-launched processes).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-06 — jevmem DB path via `${USERPROFILE}` / `${userHome}`, pin 0.3.1".

Superseded by [jevmem-0-4-config-file](jevmem-0-4-config-file.md).
