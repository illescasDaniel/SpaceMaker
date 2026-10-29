---
date: 2026-10-22
area: tooling
severity: wrong-result
status: open
---

**Call:** `uvx --from agent-guild==1.3.0 agent-guild . --tools claude,cursor,codex --with coder-python --with coder-typescript --without memory-bank`
**Expected:** Codex discovers installed project skills and receives the existing project-specific navigation-server settings.
**Got:** Skills are written to `.codex/skills` instead of the documented `.agents/skills` discovery location. Fresh Codex skills also use generic content although customized versions already exist for Claude/Cursor. New `.codex/config.toml` uses default codenav/webnav arguments without the source roots/exclusions already configured in `.mcp.json`.
**Workaround:** Share `.cursor/skills` through `.agents/skills` and `.codex/skills` symlinks; copy MCP arguments and environment from `.mcp.json`; retain the customized grader in Codex.
**Evidence:** Official skill discovery docs: https://learn.chatgpt.com/docs/build-skills (Where Codex loads local skills; symlinks supported).
**Idea:** Install Codex skills to `.agents/skills`; offer to reuse existing customized skills and migrate matching MCP server settings across tools before applying defaults.

**Local upstream fix (2026-10-22):** Implemented in `/home/daniel/Projects/Code/Agents/claude-agents` with regression coverage; 53 tests pass and the built wheel passes an install smoke test away from the checkout. Uncommitted and unreleased, so this entry stays open until published.
