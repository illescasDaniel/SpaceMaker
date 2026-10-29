---
date: 2026-10-22
area: tooling
severity: confusing
status: open
---

**Call:** `uvx --from agent-guild==1.3.0 agent-guild . --tools claude,cursor,codex --with coder-python --with coder-typescript --dry-run`
**Expected:** Shared delegation and language-routing rules become visible to all three tools through AGENTS.md.
**Got:** Existing sections in CLAUDE.md cause the installer to skip adding them to AGENTS.md; Cursor and Codex do not receive these shared rules through their primary instructions file.
**Workaround:** Move the shared sections into AGENTS.md manually and keep CLAUDE.md as an import-only shim.
**Idea:** Detect sections found only in CLAUDE.md and offer migration, or warn that the other tools cannot see them. The README documents deduplication, but this is an upgrade trap for multi-tool projects.

**Local upstream fix (2026-10-22):** Implemented in `/home/daniel/Projects/Code/Agents/claude-agents` with regression coverage; 53 tests pass and the built wheel passes an install smoke test away from the checkout. Uncommitted and unreleased, so this entry stays open until published.
