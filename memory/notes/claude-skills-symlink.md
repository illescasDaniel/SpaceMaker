---
name: claude-skills-symlink
description: Claude Code finds project skills through a .claude/skills symlink
type: decision
date: 2026-09-24
status: superseded
supersedes:
superseded_by: claude-skills-symlink-relative
source:
---

Claude Code project-skill discovery via `.claude/skills` symlink.

- **Context:** This repo's skills live under `.cursor/skills/<name>/SKILL.md` (Cursor's convention, per `AGENTS.md`'s Skills section). Claude Code's desktop app (Code tab) never showed `/save-changes`, `/apply-worktree`, etc. in autocomplete — it only auto-discovers project skills from `.claude/skills/`, with no fallback to `.cursor/skills/` the way it falls back from `CLAUDE.md` to `AGENTS.md` for instructions.
- **Decision:** Create a real OS-level directory symlink `.claude/skills -> .cursor/skills` (needs an elevated PowerShell: `New-Item -ItemType SymbolicLink -Path ".claude\skills" -Target ".cursor\skills"` after `mkdir .claude`). `core.symlinks=true` is already set for this repo, so git tracks it as one `120000` symlink blob rather than duplicating every `SKILL.md`.
- **Rationale:** A plain copy (`.claude/skills/*` duplicated from `.cursor/skills/*`) was rejected — it would drift out of sync on every future skill edit. Git Bash's `ln -s` silently falls back to a real recursive **copy** without elevated privileges/Developer Mode on Windows (confirmed: no `LinkType`, git staged `100644` not `120000`) — must use `New-Item -ItemType SymbolicLink` (or `mklink /D`) from an elevated shell, not `ln -s`, to get an actual symlink on this OS.
- **Related non-decision:** Did **not** add a `CLAUDE.md -> AGENTS.md` symlink — Claude Code already reads `AGENTS.md` natively when no `CLAUDE.md` exists (confirmed: this session loaded `AGENTS.md` as project instructions with no `CLAUDE.md` present), so that fallback needs no extra plumbing, unlike skills.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Claude Code project-skill discovery via `.claude/skills` symlink".

Superseded by [claude-skills-symlink-relative](claude-skills-symlink-relative.md).
