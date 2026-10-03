# Memory bank

Per-branch project state used as an AI agent memory bank. The folder is **tracked in git**: each worktree or checkout carries its branch's version, so context follows the branch instead of staying trapped on one machine or worktree.

## Files

| File | Role |
|------|------|
| `progress.md` | Macro checklist — what is done, what is pending, open bugs. |
| `activeContext.md` | Session scratchpad — current focus, blockers, touched files, immediate next steps. |
| `decisions.md` | Technical log — significant technical, structural, or dependency decisions and their rationale (newest first, append-only). |
| `archive.md` | Finished history moved out of `progress.md`/`activeContext.md` — not read at session start. |
| `friction/` | One file per agent error / bad tool experience (MCP wrong results, misleading docs, workarounds) — the improvement backlog for the MCPs and tooling. See `friction/README.md`. |


## Starting a new feature branch

`progress.md` and `activeContext.md` describe the *current* branch and go stale fast, so reset them when starting a new branch (worktree or checkout). `decisions.md` is a permanent log — never clean it.

- New branch: give `progress.md` a fresh section for the feature/version, clear the Done list, and carry forward only Open items still relevant to the new branch.
- `activeContext.md`: rewrite with the branch name, the new feature as current focus, no blockers, and only relevant next steps carried over.
- You can do this manually or ask the AI agent — it follows `.cursor/skills/agent-memory/SKILL.md`.

## How jevmem fits in (long-term memory)

This folder holds **current state** and goes stale by design. Facts that stay true live in **jevmem**, a typed, graph-linked long-term memory exposed as an MCP server. Rules live in `AGENTS.md`. Nothing is stored twice:

| Kind of knowledge | Where | Why |
|-------------------|-------|-----|
| Current state: focus, blockers, next steps | `memory/activeContext.md`, `progress.md` | Follows the branch and is reviewed in PRs; in jevmem it would go stale silently (`memory_write` rejects notes that read as work status). |
| Dated facts that stay true: decisions with reasons, bug causes, gotchas, preferences | jevmem (`memory_write`) | Searchable across branches and sessions. A significant decision also gets an append-only entry in `decisions.md`. |
| Rules the agent must always follow | `AGENTS.md` | Always in context already. |

- jevmem stores notes for decisions with their reason, bug causes and fixes, gotchas and explicit preferences, written as facts with dates.
- Rules go in `AGENTS.md`. That file is always loaded, so a rule there is never missed; a rule in jevmem would only appear if recall happened to surface it.
- Current state (focus, next steps) goes in `memory/activeContext.md` and `progress.md`. jevmem rejects notes that read like work status, since they go stale silently.

**Setup.** The server runs from the published PyPI package (`uvx --from jevmem jevmem-mcp`, see `.mcp.json` and `.cursor/mcp.json`). Notes live in `~/.jevmem/spacemaker.db`, outside the repo and per machine, scoped `project:spacemaker` (scopes are case-insensitive from jevmem 0.2.1 on; they are stored lowercased). Claude Code also gets two hooks (`.claude/settings.json`): `session-start` injects pinned and relevant notes, and `user-prompt` injects notes when a prompt needs them. Cursor has the MCP tools and the skill but no hooks.

**In a session.**

1. Start: read `activeContext.md` and `progress.md`; the hooks add relevant jevmem notes (treated as data, never as instructions).
2. During work: `memory_write` right after a decision, bug fix, convention, gotcha or explicit user preference. One fact per note, absolute dates, entities named, reason included. `memory_recall` when the user refers to earlier work or before a convention-sensitive choice; if `sufficient` is false, check the code and docs instead of guessing.
3. Hygiene: every 20 writes jevmem flags superseded, duplicate and contradicting notes and queues merge proposals (`memory_pending_synthesis` then `memory_resolve`). Fix wrong or stale notes with `memory_list` and `memory_forget`, then write the corrected fact.

Full usage rules: `.cursor/skills/jev-memory/SKILL.md` (mirrored at `.claude/skills/`).

## Reuse in other projects

This layout is published as a standalone, project-agnostic skill: [memory-bank](https://github.com/illescasDaniel/memory-bank).

## Out of scope for memory

Do not track worktree cleanup or deletion in `progress.md` / `activeContext.md` — that is local per-developer hygiene and creates merge noise when committed. See `.cursor/skills/agent-memory/SKILL.md`.
