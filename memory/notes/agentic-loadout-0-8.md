---
name: agentic-loadout-0-8
description: agentic-loadout 0.8.0 (formerly agent-guild): orchestrator + small/large coder tiers, Entire session history
type: context
date: 2026-11-17
status: current
supersedes: agent-guild-1-3-shared-rules
superseded_by:
source:
---

On 2026-11-17 agentic-loadout 0.8.0 (originally agent-guild) replaced the agent-guild 1.3.0 setup (commit 09f8750). The main agent orchestrates and delegates to `architect`, `coder`, `coder-small`, `coder-python(-small)`, `coder-typescript(-small)`, `code-reviewer`, `code-grader` and `utility` in `.claude/agents/`, `.cursor/agents/` and `.codex/agents/`; routing and tiers live in `.agents/development-workflow.md` and `.agents/delegation-tiers.md`, the managed guidance in `.agents/loadout-guidance.md`. Entire session history is enabled. The SpaceMaker `code-grader` body is preserved on all three tools.

**How to apply:** read `.agents/loadout-guidance.md` before changing the workflow; the project rules in `AGENTS.md` take precedence.
