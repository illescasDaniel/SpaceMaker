_Last updated: 2026-10-03 (jevmem 0.2.1 verified, documented in READMEs)_

## Branch

`feature/jevmem-trial`. jevmem runs from the published PyPI package via `uvx --from jevmem jevmem-mcp` (`.mcp.json`, `.cursor/mcp.json`, `.claude/settings.json` hooks, `.cursor/skills/jev-memory/` synced from upstream). Hooks are Claude Code only; Cursor has MCP + skill but no hooks.

## Current focus

jevmem trial wrap-up. Verified on 0.2.1 (scopes are case-insensitive, `project:SpaceMaker` recalls the same notes as `project:spacemaker`); stale note about same-size duplicates forgotten. Documented how jevmem fits (notes for decisions, bug causes, gotchas, preferences; rules in `AGENTS.md`; state in `memory/`) in the root `README.md` and `memory/README.md`.

Next: land the branch on `main`; then tackle the jevmem README known limitations (per-branch scope, instructions-file filter misses).
