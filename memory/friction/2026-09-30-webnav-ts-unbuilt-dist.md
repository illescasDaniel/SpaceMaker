---
date: 2026-09-30
area: webnav
severity: blocked
status: fixed (bin/launch.mjs installs + builds on first start)
---

**Call:** session start on `claude/webnav-typescript-port` (`.mcp.json` runs `node experiments/webnav-mcp-ts/dist/cli.js`)
**Expected:** webnav tools available
**Got:** `webnav (CONNECTION_CLOSED)`: `dist/` did not exist yet, so the host dropped the server for the whole session; nothing tells the agent to run `npm run setup:webnav`
**Workaround:** `npm run setup:webnav`, then drive `dist/cli.js` over MCP stdio from a script (no MCP restart mid-session)
**Idea:** launch through a tiny committed wrapper that builds on first run (or prints the setup command to stderr), and/or have `copy-venv.sh` build it for worktrees
