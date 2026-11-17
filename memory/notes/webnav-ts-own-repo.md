---
name: webnav-ts-own-repo
description: webnav TS port moved to its own repo webnav-ts-mcp; experiments/ dropped from SpaceMaker
type: decision
date: 2026-09-30
status: superseded
supersedes: webnav-ts-launcher-self-builds
superseded_by: webnav-consume-published-npm
source:
---

webnav TS port extracted to its own repo `webnav-ts-mcp`.

- **Context:** The port lived in `experiments/webnav-mcp-ts/` (prototype, inside SpaceMaker). It works and is meant to be published on npm so SpaceMaker can consume it as a package.
- **Decision:** (1) Moved it to `~/Projects/Code/Python/MCPs/webnav-ts-mcp` (git-initialised, MIT, author/version like the Python package, npm name `webnav-ts-mcp`, version 0.1.0, bin `webnav-ts-mcp`). Nothing of it remains in SpaceMaker: dropped `experiments/`, the `setup:webnav` script and the root `biome.json` `!!**/experiments` ignore. (2) Until it is on npm, `.mcp.json` / `.cursor/mcp.json` launch `${HOME}/Projects/Code/Python/MCPs/webnav-ts-mcp/bin/launch.mjs` (Cursor: `${env:HOME}`); after publishing, switch both to `npx webnav-ts-mcp`. (3) `scripts/bench.mjs` (new, in the package) measures speed/memory against the Python server.
- **Result:** package `npm run check` 152 tests, parity 71/71 + SpaceMaker scenario, tarball (51 kB) installed into an empty project and all 12 tools driven over `npx webnav-ts-mcp`. Vs Python (median of 7): cold start 103 ms vs 528 ms, whole session 1.6 s vs 3.5 s, warm calls 2-5x faster, memory 359 vs 477 MiB.
- **Open:** publish (owner needs `npm login`); then switch the host configs to `npx`; Windows/macOS/Node 20 unverified.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — webnav TS port extracted to its own repo `webnav-ts-mcp`".

Superseded by [webnav-consume-published-npm](webnav-consume-published-npm.md).
