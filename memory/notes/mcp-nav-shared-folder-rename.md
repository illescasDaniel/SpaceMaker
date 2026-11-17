---
name: mcp-nav-shared-folder-rename
description: _shared folder renamed mcp-nav-shared, import name kept _shared
type: decision
date: 2026-09-28
status: superseded
supersedes:
superseded_by: mcp-nav-shared-import-name
source:
---

Rename shared MCP folder `_shared` → `mcp-nav-shared`.

- **Context:** After the uv workspace split, the on-disk folder was still `mcp-servers/_shared/` while the distribution name was already `mcp-nav-shared` — easy to confuse when browsing the tree or editing workspace member paths.
- **Decision:** `git mv mcp-servers/_shared mcp-servers/mcp-nav-shared`. Python import name stays `_shared` (`[tool.uv.build-backend] module-name = "_shared"`). Updated workspace members, ty `root`, `pytest.sh`, `docs/agent-tooling.md` paths, and the package-path assertion in `test_workspace.py`.
- **Rationale:** Folder name matching the distribution name removes the last naming split that wasn't load-bearing; renaming the import package would have been pure churn for no packaging benefit.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Rename shared MCP folder `_shared` → `mcp-nav-shared`".

Superseded by [mcp-nav-shared-import-name](mcp-nav-shared-import-name.md).
