_Last updated: 2026-09-30 (webnav TypeScript port prototype on `claude/webnav-typescript-port`)_

## Branch

`claude/webnav-typescript-port`: webnav is the published npm package `webnav-ts-mcp` (own repo `~/Projects/Code/Python/MCPs/webnav-ts-mcp`); `.mcp.json`/`.cursor/mcp.json` launch it with `npx --yes webnav-ts-mcp@^0.1.1`. Otherwise primary checkout `main`. Worktree `faak` / `cursor/094eb8f7` still on disk.

## Current focus

MCP servers live in their own repos (`~/Projects/Python/MCPs/{mcp-nav-shared,codenav-mcp,webnav-mcp}`, public on GitHub). 0.1.1 of all three is on PyPI; SpaceMaker depends on `codenav-mcp>=0.1.1` / `webnav-mcp>=0.1.1` (locked with `mcp-nav-shared` 0.1.1).

## Just changed

- Published 0.1.1 (TestPyPI, then PyPI; fresh-venv handshake verified on both). Each repo's `test-package` now takes only its own packages from TestPyPI (`--no-deps`) and passes `--refresh` (uv's first-index rule and cached index pages otherwise hide new versions).
- `docs-build`: 19 links from docs to files outside `docs/` (specs, packaging, tests, memory) rewritten to absolute GitHub URLs; zero warnings left.
- Live codenav/webnav MCP calls verified on this repo. `~/.pypirc` is 600.

## Next steps

1. Bumped configs to `webnav-ts-mcp@^0.1.1` (2026-09-30); verified live after MCP restart: outline, callers, symbol_info, selector correct; `implementations` returns "none" for `PywebviewApi` (web/src has no classes, so the positive case is only covered by the package's own tests).
2. `/apply-worktree` to land this branch on `main`.
3. `/delete-worktree` for `faak` when finished with it.
4. Still open: verify webnav-ts-mcp on Windows/macOS/Node 20.
