---
name: webnav-runs-typescript-port
description: SpaceMaker's webnav switched to the TS port from experiments/; Python webnav-mcp dropped from deps
type: decision
date: 2026-09-30
status: superseded
supersedes: webnav-typescript-port-prototype
superseded_by: webnav-ts-launcher-self-builds
source:
---

SpaceMaker's webnav MCP now runs the TypeScript port; inherited lookup, `callers`, `implementations`.

- **Context:** After the prototype proved parity, the owner asked to switch this branch's MCP configs to it (no publishing yet), and to fix inherited-member lookup and add `callers`/`implementations`. TypeScript 7's LSP has no type hierarchy (the old `resolve_inherited` path is dead for TS) but does offer call hierarchy and `textDocument/implementation`.
- **Decision:** (1) `.mcp.json` / `.cursor/mcp.json` run `node <project>/experiments/webnav-mcp-ts/dist/cli.js` with the same `WEBNAV_MCP_*` env. `dist/` and `node_modules/` stay uncommitted; `npm run setup:webnav` (root script: `npm ci` + build in the package) creates them. (2) Removed `webnav-mcp` from the root `pyproject.toml`/`uv.lock` (only that package changed in the lock). (3) `Class.member` inheritance: read `extends`/`implements` clauses from source, resolve each base with `definition`, walk BFS across files; library/`.d.ts`/`node_modules` bases skipped. (4) New tools `callers` (call hierarchy) and `implementations` (LSP implementation, minus the symbol itself, qualified `Class.method` labels). (5) `scripts/parity.mjs` now tolerates TS-only tools and lists intentional differences.
- **Rationale / trade-off:** the config points at a build artifact, so a fresh clone or worktree needs one setup command before webnav works (documented in AGENTS.md, README, `agent-tooling.md`); accepted while the port is a prototype. Python `webnav-mcp` is untouched and still usable elsewhere. Still Linux + Node 22 only.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — SpaceMaker's webnav MCP now runs the TypeScript port; inherited lookup, `callers`, `implementations`".

Superseded by [webnav-ts-launcher-self-builds](webnav-ts-launcher-self-builds.md).
