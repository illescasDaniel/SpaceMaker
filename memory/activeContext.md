_Last updated: 2026-10-08 (jevmem 0.4.0 verified on Linux)_

## Branch

`main`. webnav `npx --yes webnav-ts-mcp@^0.2.0`; codenav `codenav-mcp>=0.2.0,<0.3`; jevmem `>=0.4.0,<0.5`. Secret gate on `smart-commit-guard` 0.2.0.

## Current focus

Nothing in flight. Latest: jevmem 0.4.0 config switch (`.mcp.json`, `.cursor/mcp.json`, hooks in `.claude/settings.json`, README, jev-memory skill).

## Just changed

- jevmem MCP entries have no env block: key and DB path live in `~/.jevmem/config.jsonc` (`uvx jevmem config init --api-key ...`), outside the repo. Notes default to `project:spacemaker`; `scope="global"` for personal preferences. Verified over MCP with public 0.4.0 on Claude Code and on Cursor (no-scope write lands in `project:spacemaker`, global write, recall of both; no env needed).

- jevmem 0.4.0 verified on Linux (2026-10-08): created `~/.jevmem/config.jsonc` from the old `~/.jevmem/.env` key and set `"db": "~/.jevmem/spacemaker.db"` (0.4.0 defaults to an empty `memory.db`); CLI, both hooks and the MCP (79 nodes, recall works) pass after a restart. `memory/README.md` Setup paragraph updated.

## Next steps

- Optional cleanup: jevmem notes 7 and 8 (Cursor test notes, one project and one global) are still in `~/.jevmem/spacemaker.db`; remove with `memory_forget` (the auto-mode classifier denied it for the agent).
- `.claude/settings.json` jevmem hooks now run `uvx --from "jevmem>=0.4.0,<0.5" jevmem hook ...` with no env prefix (DB from `config.jsonc`, scope derived from the repo name); verified both hooks return recalled notes.
