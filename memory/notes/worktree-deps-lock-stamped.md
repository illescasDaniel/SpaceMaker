---
name: worktree-deps-lock-stamped
description: node_modules copied only when lockfiles match (stamp), else npm ci; .venv always uv sync
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

Worktree deps: lock-stamped `node_modules`, always-`uv sync` `.venv`.

- **Context:** A worktree made with a bare `git worktree add` had no `node_modules`, so the web gate failed. `copy-venv.sh` also kept any working `.venv`/`node_modules` even when the branch's lockfiles differed.
- **Decision:** `copy-venv.sh` runs `uv sync --group dev` (offline first) on a kept `.venv`. `node_modules` gets a `.spacemaker-lock-hash` stamp (blob hash of `package-lock.json`); it is copied from the primary only when lockfiles are identical, else `npm ci --prefer-offline`. AGENTS.md tells agents to run the script directly in any linked worktree.
- **Rationale:** Copying is fast but wrong when lockfiles diverge; a stamp is a cheap, offline staleness check.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Worktree deps: lock-stamped `node_modules`, always-`uv sync` `.venv`".
