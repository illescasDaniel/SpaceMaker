_Last updated: 2026-09-30 (TS7 committed; applying worktree to main)_

## Branch

Worktree `faak` (`cursor/094eb8f7`) — TypeScript 7 + webnav native `tsc` LSP.

## Current focus

`/save-changes` (no push) then `/apply-worktree` into primary checkout `main`.

## Just changed

- Root `typescript@^7`, dropped `typescript-language-server`; webnav owns package-local `tsc` LSP tooling.
- Live webnav MCP verified after restart (`symbol_info`/`hover`/`diagnostics`/`outline`/`search_symbol` on TS7).

## Next steps

1. Merge `cursor/094eb8f7` into primary `main` checkout; run `uv run task checks`.
2. Restart webnav MCP on primary after apply if needed.
3. Optional later: publish MCP packages (PyPI token); `/delete-worktree` when done with `faak`.
