---
date: 2026-09-30
area: tooling
severity: blocked
status: fixed (root biome.json force-ignores `!!**/experiments`)
---

**Call:** `uv run task checks` (web step: `biome check .` at the repo root)
**Expected:** web check passes; `files.includes` doesn't list `experiments/`
**Got:** `Found a nested root configuration` for `experiments/webnav-mcp-ts/biome.json` (`"root": true`); Biome indexes nested configs even outside `files.includes`
**Workaround:** none needed after the fix
**Idea:** any future self-contained package under the repo needs the same force-ignore (`!!`), not a plain `!`
