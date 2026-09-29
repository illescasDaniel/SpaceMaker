---
date: 2026-09-29
area: docs
severity: confusing
status: fixed (6540add)
---

**Source:** subagent working on `.thumb-removing`.
**Call:** `webnav.selector(query=".thumb-removing")` -> pydantic validation error (param is `name`); agent gave up on the MCP and used grep.
**Cause:** deferred MCP tools have no visible schema until fetched; subagent guessed the param name. One failed call was enough to abandon the tool.
**Idea:** give delegated-agent prompts a concrete example call, or add the examples proposed in `2026-09-29-agents-skip-mcps-and-grep.md` to AGENTS.md. Consider aliasing `query` on `selector`/`css_var` (cheap, forgiving).
