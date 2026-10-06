_Last updated: 2026-10-06 (jevmem 0.4.0 adopted, verified on Claude Code)_

## Branch

`main`. webnav `npx --yes webnav-ts-mcp@^0.2.0`; codenav `codenav-mcp>=0.2.0,<0.3`; jevmem `>=0.4.0,<0.5`. Secret gate on `smart-commit-guard` 0.2.0.

## Current focus

Nothing in flight. Latest: jevmem 0.4.0 config switch (`.mcp.json`, `.cursor/mcp.json`, hooks in `.claude/settings.json`, README, jev-memory skill).

## Just changed

- jevmem MCP entries have no env block: key and DB path live in `~/.jevmem/config.jsonc` (`uvx jevmem config init --api-key ...`), outside the repo. Notes default to `project:spacemaker`; `scope="global"` for personal preferences. Verified over MCP with public 0.4.0 (project write, global write, recall of both).

## Next steps

- Re-test `.cursor/mcp.json` in Cursor on public 0.4.0 and confirm the derived scope is `project:spacemaker` (if not, set `JEVMEM_REPO`/`JEVMEM_SCOPE` there). The local build passed all 4 steps.
- `.claude/settings.json` jevmem hooks now run `uvx --from "jevmem>=0.4.0,<0.5" jevmem hook ...` with no env prefix (DB from `config.jsonc`, scope derived from the repo name); verified both hooks return recalled notes.
