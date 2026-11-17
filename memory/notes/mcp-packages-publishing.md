---
name: mcp-packages-publishing
description: console scripts and documented uvx install; ty lookup order; SpaceMaker ran the editable source
type: decision
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

MCP packages: how they're published.

- **Context:** Final pass before publishing `mcp-nav-shared`, `codenav-mcp` and `webnav-mcp` to PyPI. Testing the built wheels outside the repo showed codenav couldn't start ty, LICENSE wasn't shipped, there was no console entry point, and the READMEs' relative links and SpaceMaker-specific tool examples would be wrong for everyone else.
- **Decision:** (1) Console scripts `codenav-mcp`/`webnav-mcp` → `server:main`; the documented install is `uvx codenav-mcp`. SpaceMaker's own `.mcp.json` keeps `uv run python -m …` so it runs the workspace's editable source. (2) ty order: workspace `.venv` ty → ty bundled with codenav (`ty.find_ty_bin()`) → PATH → `uvx ty server`. (3) The servers pin `mcp-nav-shared>=0.1.0,<0.2`: in 0.x any minor may break the shared API, and a shared change ships first. (4) Package READMEs are PyPI pages: absolute links only, generic examples; SpaceMaker wiring stays in `docs/agent-tooling.md`. (5) Tool descriptions use generic examples (`UserService.create_user`, `.card-title`); AGENTS.md keeps the repo-specific ones.
- **Rationale:** The project's own ty goes first so its version matches its config; the bundled one guarantees codenav works with nothing else installed. Release checks must run from wheels in a clean environment, since this repo's `.venv` hid the ty bug. Tool descriptions reach every user's agent, and an example naming a symbol that doesn't exist in their project misleads more than it helps.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — MCP packages: how they're published".
