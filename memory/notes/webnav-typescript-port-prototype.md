---
name: webnav-typescript-port-prototype
description: prototype TS port of webnav under experiments/ with identical tool names and output
type: decision
date: 2026-09-30
status: superseded
supersedes:
superseded_by: webnav-runs-typescript-port
source:
---

Prototype: TypeScript port of webnav-mcp (`experiments/webnav-mcp-ts/`).

- **Context:** webnav was written in Python because it grew out of codenav (which must be Python: it drives `ty`) and shares `mcp-nav-shared`. But webnav itself only spawns Node language servers and scans web files, and its audience is web projects, where `pip`/`uv` is friction next to `npm`.
- **Decision:** (1) Port webnav and the webnav-relevant part of `mcp-nav-shared` (LSP client, format, resolve, workspace, notices, errors, params, exclude) to TypeScript as a prototype under `experiments/webnav-mcp-ts/` (outside `src/spacemaker/`, so no SDD gate; not published). (2) Keep the tool/parameter/env-var names and output text identical to the Python package, and prove it with `scripts/parity.mjs` (drives both servers over MCP stdio and diffs). (3) The shared code stays an internal `src/shared/` directory, not a second npm package, until a second TS server exists. (4) Language servers become plain npm dependencies (project's TS >= 7 wins, else the bundled one), launched via `node`, so there is no runtime download / `npx --yes` fallback.
- **Result:** feasible. Parity 37/37 (SpaceMaker web assets) and 71/71 (fixture incl. edits behind the servers' backs, restart notice); 126 vitest tests; tarball installed into a fresh app with its own TypeScript 5 works via `npx webnav-mcp`. Cold start 0.28 s vs 1.0 s. Found and fixed one real bug the Python side doesn't have: the MCP SDK's stdio server ignores stdin EOF, orphaning language servers (`cli.ts` handles it; regression test). Costs: ~177 MB `node_modules` in an app on TS 5 (same npm payload the Python package needed), the shared layer exists twice (parity script is the drift guard).
- **Open:** publish under the npm name `webnav-mcp` (free as of 2026-09-30)? Retire the Python webnav or keep both? Verify Windows/macOS/Node 20. Not decided; needs the owner's call.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — Prototype: TypeScript port of webnav-mcp (`experiments/webnav-mcp-ts/`)".

Superseded by [webnav-runs-typescript-port](webnav-runs-typescript-port.md).
