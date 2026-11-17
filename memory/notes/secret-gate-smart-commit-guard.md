---
name: secret-gate-smart-commit-guard
description: tracked .githooks/pre-commit + CI scan; rules block, a local model only judges ambiguous hits
type: decision
date: 2026-10-05
status: superseded
supersedes:
superseded_by: secret-gate-smart-commit-guard-0-2
source:
---

Secret gate: `smart-commit-guard` via a tracked `.githooks/pre-commit` plus a CI scan.

- **Context:** nothing stopped a key, password or `.env` from being committed. A first package name, `secret-guard`, was rejected by PyPI as too similar to existing projects, so the package is `smart-commit-guard` 0.1.0 (own repo, standalone: not part of jevmem, no MCP, CLI only).
- **Decision:** `.githooks/pre-commit` (tracked, activated per clone with `git config core.hooksPath .githooks`, `.gitattributes` keeps LF) runs `uvx --from 'smart-commit-guard>=0.1,<0.2' ... scan --staged`; `.github/workflows/secret-scan.yml` runs the same rules without a model on pull requests and pushes. The model is the local ollaya `jevk5:4b` and only judges ambiguous candidates; if it is down they warn and rule hits still block. `SKIP_SECRET_GUARD=1` bypasses the hook once and is logged; CI ignores it.
- **Rationale:** rules catch the obvious cases for free; the small model removes the placeholder-versus-real false positives regex cannot. The uvx pin avoids stale cache, as with the MCP packages. A whole-tree scan of SpaceMaker has 0 blocks and ~27 model-less warnings, all test fixtures.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-05 — Secret gate: `smart-commit-guard` via a tracked `.githooks/pre-commit` plus a CI scan".

Superseded by [secret-gate-smart-commit-guard-0-2](secret-gate-smart-commit-guard-0-2.md).
