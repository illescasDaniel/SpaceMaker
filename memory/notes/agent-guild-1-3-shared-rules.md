---
name: agent-guild-1-3-shared-rules
description: AGENTS.md as the rules source, CLAUDE.md an import shim, one skill source shared by Claude, Cursor and Codex
type: decision
date: 2026-10-22
status: superseded
supersedes:
superseded_by: agentic-loadout-0-8
source:
---

Agent-guild 1.3.0: shared project rules and skills across three tools.

- **Context:** Reinstall requested after agent-guild added AGENTS.md and Codex support; the previous install kept delegation rules only in CLAUDE.md and SpaceMaker already customized skills and its grader.
- **Decision:** Keep AGENTS.md as the rules source, CLAUDE.md as an import-only shim, native agents per tool, and one skill source in `.cursor/skills` exposed through `.claude/skills`, `.codex/skills` and the supported `.agents/skills` discovery path. Preserve project customizations without `--force`; use existing agent-memory rather than installing a redundant memory-bank. Align Codex MCP args/env with `.mcp.json` and explicitly load the hexagonal rule from AGENTS.md for Codex.
- **Rationale:** All tools receive the same project policies and customized skills; Claude still needs the import shim. Shared symlinks avoid generic Codex copies drifting from approved SpaceMaker workflows. Official skill path: https://learn.chatgpt.com/docs/build-skills.

Commit: cfcc18f (2026-10-22) installed agent-guild and aligned SDD; the 1.3.0 reinstall described here was committed later.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-22 — Agent-guild 1.3.0: shared project rules and skills across three tools".

Superseded by [agentic-loadout-0-8](agentic-loadout-0-8.md).
