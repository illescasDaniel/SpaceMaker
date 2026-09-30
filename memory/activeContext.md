_Last updated: 2026-09-30 (webnav TypeScript port prototype on `claude/webnav-typescript-port`)_

## Branch

`claude/webnav-typescript-port`: prototype of webnav in TypeScript (`experiments/webnav-mcp-ts/`), awaiting a go/no-go. Otherwise primary checkout `main`. Worktree `faak` / `cursor/094eb8f7` still on disk.

## Current focus

MCP servers live in their own repos (`~/Projects/Python/MCPs/{mcp-nav-shared,codenav-mcp,webnav-mcp}`, public on GitHub). 0.1.1 of all three is on PyPI; SpaceMaker depends on `codenav-mcp>=0.1.1` / `webnav-mcp>=0.1.1` (locked with `mcp-nav-shared` 0.1.1).

## Just changed

- Published 0.1.1 (TestPyPI, then PyPI; fresh-venv handshake verified on both). Each repo's `test-package` now takes only its own packages from TestPyPI (`--no-deps`) and passes `--refresh` (uv's first-index rule and cached index pages otherwise hide new versions).
- `docs-build`: 19 links from docs to files outside `docs/` (specs, packaging, tests, memory) rewritten to absolute GitHub URLs; zero warnings left.
- Live codenav/webnav MCP calls verified on this repo. `~/.pypirc` is 600.

## Next steps

1. Restart the MCPs once more (they report "own code changed" after the mid-session `mcp-nav-shared` upgrade).
2. `/delete-worktree` for `faak` when finished with it.
