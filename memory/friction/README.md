# Agent friction log

Every error, wrong/misleading tool result, slowdown, or "had to fall back to grep" an AI agent hits while working here. Purpose: a backlog for improving the **MCP servers** (`codenav`, `webnav`), the docs/skills, and the code itself. Unlike `decisions.md` (why we chose X) this records *what hurt*.

## Rules for agents

- **Log at the moment of friction**, then keep working — one small file per entry, don't batch to end of session.
- One file per entry (`YYYY-MM-DD-short-slug.md`) so parallel branches/worktrees never merge-conflict on a shared file. Never edit history; when fixed, only flip `status`.
- Log: MCP tool wrong/missing/misleading/slow results; docs that lied; a Phase-Gate or tooling rule that blocked legitimate work; a workaround you needed. Don't log your own typos or one-off user-environment issues.
- Include enough to reproduce (exact tool call + what you expected vs. got). Redact secrets/personal paths.

## Entry template

```markdown
---
date: YYYY-MM-DD
area: codenav | webnav | mcp-nav-shared | docs | tooling | code
severity: wrong-result | missing-feature | slow | confusing | blocked
status: open | fixed (<commit or PR>) | wontfix (<why>)
---

**Call:** `selector("#btn-x")`
**Expected:** JS usage in web/src/gallery.ts
**Got:** no JS hits
**Workaround:** grep
**Idea:** (optional) how the tool/doc could avoid this
```

## Triage

Whoever works on the MCPs reads entries with `status: open` first: `grep -l "status: open" memory/friction/*.md`. Move fixed entries older than ~a month to `memory/archive.md` in bulk if the directory gets long.
