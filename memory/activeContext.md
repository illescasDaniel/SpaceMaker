_Last updated: 2026-10-22_

## Branch and focus

Download all feature (specs/download-all): implemented, round-2 grade pending, uncommitted. Older note: `main`. Agent-guild 1.3.0 reinstalled for Claude Code, Cursor and Codex. No app behavior or production source changed; this was tooling maintenance, with no SDD feature gate pending.

## Completed

- Installer: `uvx --from agent-guild==1.3.0 agent-guild . --tools claude,cursor,codex --with coder-python --with coder-typescript --without memory-bank`; no force. Kept SpaceMaker's `agent-memory`, customized SDD/jev-memory skills and grader.
- Shared delegation/language rules moved into `AGENTS.md` (119 lines, budget 130). `CLAUDE.md` is only `@AGENTS.md` so Claude imports the shared instructions.
- Native Cursor and Codex agents installed; Codex grader uses the SpaceMaker body. `.agents/skills` and `.codex/skills` link to `.cursor/skills`. Codex MCP arguments/env match `.mcp.json`. Codex explicitly loads the hexagonal rule through AGENTS.md guidance.
- Fixed invalid unquoted Claude language-agent descriptions. Updated `docs/agent-tooling.md`. Touched agent configs, instructions, skill symlinks, docs and memory only.
- Verification: 10 agent-context tests pass; six Codex TOMLs parse; MCP configs match; shared skill paths and Claude import verified; installer rerun dry-run preserves local changes. Full app suite not needed for this configuration-only change. `uv run` cache was read-only in sandbox, so tests used `.venv/bin/python` directly.

## Upstream fixes completed (2026-10-22)

User authorized fixes in `/home/daniel/Projects/Code/Agents/claude-agents`. Seven files changed there: installer, vendors, specialists, rules template, tests, README and CHANGELOG. Codex installs to `.agents/skills`, reuses existing project skills/MCP settings, migrates shared CLAUDE rules, uses an explicit workflow-reading instruction, and quotes language-coder descriptions. Baseline 39 tests; now 53 pass. Eight new cases fail against original 1.3.0 as expected. Offline wheel/sdist build and built-wheel install smoke away from checkout pass. No version bump, commit, push or release. No agent-guild instructions file or memory bank existed in that checkout.

## Next step

Restart the coding tool to load the new project agents, skills and MCP configuration. Changes are uncommitted; no commit requested. Local upstream fixes are ready for review/commit and a later release. Installation findings are in the three `2026-10-22-agent-guild-*` friction entries. Earlier app context is preserved in `memory/archive.md`; app follow-ups remain in `memory/progress.md` (some older “uncommitted” notes predate the commits visible in git).
