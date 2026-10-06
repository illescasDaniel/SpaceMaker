_Last updated: 2026-10-06 (jevmem 0.3.1 adopted, Windows verified)_

## Branch

`main`. webnav `npx --yes webnav-ts-mcp@^0.2.0`; codenav `codenav-mcp>=0.2.0,<0.3`; jevmem `>=0.3.1,<0.4`. Secret gate on `smart-commit-guard` 0.2.0.

## Current focus

Nothing in flight. Latest: jevmem 0.3.1 config switch (`.mcp.json`, `.cursor/mcp.json`).

## Just changed

- jevmem configs pin `>=0.3.1,<0.4`; DB path uses `${USERPROFILE}` (Claude Code) / `${userHome}` (Cursor) because `${HOME}` is unset on Windows. Verified over MCP with the public 0.3.1 package.

## Next steps

- Verify `.cursor/mcp.json` in Cursor itself: `${userHome}` is documented for the desktop IDE but untestable from here (forum reports it is not expanded in cloud agents).
- `.claude/settings.json` jevmem hooks keep the bash-style env prefix on purpose: hook entries have no per-hook `env`, so exec form cannot set `JEVMEM_DB`; they work on Windows via Git Bash (verified 2026-10-06). Revisit only if jevmem gains a `--db` flag or a PowerShell-only user needs it.
