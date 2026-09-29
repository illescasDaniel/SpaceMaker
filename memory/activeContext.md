_Last updated: 2026-09-29_

## Branch

`claude/typescript-python-type-hints-0b69dc`

## Current focus

`web/src/*.ts` typing refactor is done and fully verified: `npm run check` / `uv run task checks` green, guard-rail test passing, docs/memory updated, and a browser-pane smoke test (2026-09-29, `spacemaker-server` on :8765) confirmed Home/Gallery (timeline + calendar + item nav)/Settings/USB file transfer all boot and route with zero console/server errors. Task is complete pending user review.

## Next steps

1. Ready for review/PR — not yet requested by the user.

## Just changed

- All 18 `web/src/*.ts` modules: removed `@ts-nocheck`, fully typed, dropped the `R` registry, `./x.js` → `./x.ts` imports.
- `biome.json`: `noExplicitAny`/`noTsIgnore`/`noVar` errors scoped to `web/src/**/*.ts` via `overrides`.
- New `tests/unit/test_web_typing.py` guard-rail test (passing).
- `scripts/quality/checks.py` / `ruff.sh` / `pyproject.toml`: ruff now covers `mcp-servers`; fixed a pre-existing pytest `test_server.py` collision (`--import-mode=importlib`).
- Docs: `docs/ARCHITECTURE.md`, `docs/agent-tooling.md` describe the new import/typing conventions.
- See `memory/decisions.md` 2026-09-29 for full rationale.
