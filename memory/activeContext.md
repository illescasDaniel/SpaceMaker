_Last updated: 2026-10-04 (codenav via uvx verified)_

## Branch

`worktree-codenav-local-write-tools-trial`, merged to `main` after the final check. codenav now starts with `uvx --from "codenav-mcp>=0.2.0,<0.3" codenav-mcp` in `.mcp.json` and `.cursor/mcp.json` (own isolated env, no longer a dev dependency; `ty` still reads the project's `.venv`). Published `codenav-mcp` 0.2.1 adds `--help`/`--version`; the README got PyPI badges (no release for that).

## Current focus

Verified live over `uvx` on 0.2.1 (symbol lookup, create/edit-refused/rename/outline). Docs updated in `docs/agent-tooling.md`.

Next: fix the pre-existing docs-build warning (`ARCHITECTURE.md` links `../specs/network-passcode/SPEC.md`, outside `docs/`; use an absolute GitHub URL); codenav idea: skip gitignored paths (e.g. `site/`) in the rename mention scan; jevmem README known limitations.
