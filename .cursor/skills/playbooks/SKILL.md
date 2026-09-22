---
name: playbooks
description: Read SpaceMaker playbooks for architecture, SDD, and testing. Use when layer boundaries or conversion policy is unclear.
---

# Playbooks Reference Skill

## Read order

1. `memory/activeContext.md` then `memory/progress.md`
2. `AGENTS.md`
3. `docs/playbooks/SpaceMaker-adaptations.md`
4. As needed:
   - `hexagonal-architecture.md`
   - `spec-driven-development.md`
   - `fast-tests.md`
5. Feature spec: `specs/<feature>/SPEC.md`
6. Wireframe: path from spec metadata

## Do not

- Put FFmpeg flag details only in adapters without matching spec/adaptations doc
- Skip wireframe gate for new UI or implement in `src/` before explicit design + spec approval (see `AGENTS.md` Phase Gate Protocol)
- Import adapters from domain/application
