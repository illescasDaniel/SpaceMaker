# Reference Playbooks

Playbooks live under `docs/playbooks/`.

## Before architectural or feature work

1. Read `memory/activeContext.md` and `memory/progress.md` (see `agent-memory.md`)
2. Read `AGENTS.md` (Phase Gate Protocol)
3. Read `docs/playbooks/SpaceMaker-adaptations.md` (project-specific overrides)
4. Read when you need deeper context:
   - `docs/playbooks/hexagonal-architecture.md`
   - `docs/playbooks/spec-driven-development.md`
   - `docs/playbooks/fast-tests.md`

## Priority when docs conflict

`specs/<feature>/SPEC.md` → `docs/playbooks/SpaceMaker-adaptations.md` → `.claude/rules/` (and `.cursor/rules/`) → playbooks → generic examples in playbooks.

## Skills

Use `.cursor/skills/sdd-feature/`, `hexagonal-python/`, `playbooks/`, `agent-memory/`, `fast-tests/` for this repo's workflows (mirrored at `.claude/skills/`).
