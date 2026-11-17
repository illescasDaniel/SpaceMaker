---
name: mcp-nav-shared-import-name
description: shared package import name aligned to mcp_nav_shared
type: decision
date: 2026-09-28
status: current
supersedes: mcp-nav-shared-folder-rename
superseded_by:
source:
---

Align `mcp-nav-shared` import name with distribution name.

- **Context:** Folder was renamed to `mcp-servers/mcp-nav-shared`, but the Python import stayed `_shared` via `[tool.uv.build-backend] module-name = "_shared"`, leaving a confusing split.
- **Decision:** Renamed `src/_shared/` → `src/mcp_nav_shared/`, dropped the `module-name` override (uv's default for `mcp-nav-shared` is `mcp_nav_shared`), and updated all `from _shared…` imports in codenav/webnav/tests/docs.
- **Rationale:** Distribution, folder, and import should read as one package; the underscore import is the normal Python spelling of the hyphenated dist name.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Align `mcp-nav-shared` import name with distribution name".
