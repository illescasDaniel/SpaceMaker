---
name: mcp-packages-separate-repos
description: codenav-mcp, webnav-mcp and mcp-nav-shared live in their own repos; SpaceMaker uses the PyPI releases
type: decision
date: 2026-09-30
status: current
supersedes: mcp-servers-uv-workspace
superseded_by:
source:
---

MCP packages extracted into separate repos.

- **Context:** After publishing 0.1.0, keeping `mcp-servers/` as a uv workspace in SpaceMaker tied three independently-published packages to an app repo (their PyPI URLs, issues and history all lived under SpaceMaker).
- **Decision:** (1) One git repo per package under `~/Projects/Python/MCPs/` (`mcp-nav-shared`, `codenav-mcp`, `webnav-mcp`), public on GitHub `illescasDaniel/<name>`, fresh history (no filter-repo). (2) SpaceMaker consumes the **PyPI** packages as plain dev dependencies; no workspace, no path sources; unreleased changes are tried with `uv pip install -e`. (3) Publishing tooling moved with them (per-repo `uploader` group, `upload`/`test-package` tasks) and was removed from SpaceMaker. (4) Repo versions bumped to 0.1.1 because 0.1.0's PyPI metadata links to paths that no longer exist; SpaceMaker pins `>=0.1.0` until 0.1.1 is published.
- **Rationale:** Package repos get their own issues/releases/CI story; SpaceMaker's gate no longer lints/tests other projects; depending on PyPI proves the published artifacts are what the app really runs on (verified: both servers answer real calls from `.mcp.json`-style launch).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — MCP packages extracted into separate repos".
