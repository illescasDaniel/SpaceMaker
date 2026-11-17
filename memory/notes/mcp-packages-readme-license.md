---
name: mcp-packages-readme-license
description: standalone MCP packages ship README and MIT LICENSE
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Standalone MCP packages ship README + MIT LICENSE.

- **Context:** Docs front doors only mentioned `codenav`; the three uv-workspace packages under `mcp-servers/` had no package README or LICENSE and omitted `license`/`readme`/`authors` in `pyproject.toml`, which is weak for installable-outside-monorepo reuse.
- **Decision:** Added `README.md` + MIT `LICENSE` (same copyright as the repo root) to `mcp-nav-shared`, `codenav-mcp`, and `webnav-mcp`; set `license`/`readme`/`authors` on each `[project]`. Updated SpaceMaker front doors (root README, `docs/index.md`, `ARCHITECTURE.md`, `AGENTS.md` Orient, `agent-tooling.md` At a glance) to name both servers and link the package READMEs. No parent `mcp-servers/README.md` — package READMEs + `docs/agent-tooling.md` are the two layers.
- **Rationale:** Standalone consumers need self-contained package docs and an unambiguous license next to the `pyproject.toml`; SpaceMaker-specific agent wiring stays in `docs/agent-tooling.md` to avoid duplicating a second deep source of truth.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Standalone MCP packages ship README + MIT LICENSE".
