_Last updated: 2026-09-29_

## Branch

`claude/code-grading-sdd-feature-14ecc1`

## Current focus

Added SDD Phase 5 (`code-grader` subagent + `grade_prechecks.py`). Implemented and tests written; awaiting user review and a first real-feature trial.

## Next steps

Trial `code-grader` on the next real SDD feature (agent files were never spawned; confirm the Cursor agent loads). Other open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).

## Just changed

- `.claude/agents/code-grader.md`, `.cursor/agents/code-grader.md`, `scripts/quality/grade_prechecks.py`, `tests/unit/test_grade_prechecks.py`, drift tests in `test_agent_context.py`, `sdd-feature` skill Phase 5, AGENTS/docs/memory. Also moved `managed_tools.py` application→bootstrap/services (layering fix). See `decisions.md` 2026-09-29.

- All 18 `web/src/*.ts` modules typed, `R` registry dropped, `./x.ts` imports; Biome strict rules scoped to `web/src/**/*.ts`; guard-rail test `tests/unit/test_web_typing.py`.
- ruff covers `mcp-servers`. `main` also renamed the colliding `test_server.py` files; `--import-mode=importlib` remains as a belt-and-braces setting.
- See `memory/decisions.md` 2026-09-29 for rationale.
