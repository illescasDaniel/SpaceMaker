_Last updated: 2026-09-29_

## Branch

`claude/typescript-python-type-hints-0b69dc` (merged with latest `main` 2026-09-29)

## Current focus

`web/src/*.ts` typing refactor is done and verified; latest `main` (smooth scrolling, 304 thumb fix, `-version` fix, quality-gate fixes) merged in. Ready to apply to `main`.

## Next steps

Open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).

## Just changed

- All 18 `web/src/*.ts` modules typed, `R` registry dropped, `./x.ts` imports; Biome strict rules scoped to `web/src/**/*.ts`; guard-rail test `tests/unit/test_web_typing.py`.
- ruff covers `mcp-servers`. `main` also renamed the colliding `test_server.py` files; `--import-mode=importlib` remains as a belt-and-braces setting.
- See `memory/decisions.md` 2026-09-29 for rationale.
