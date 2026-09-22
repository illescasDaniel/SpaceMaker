---
name: sdd-feature
description: Run Spec-Driven Development for SpaceMaker features. Use when adding or changing user-facing flows, wireframes, SPEC.md, or implementing from acceptance criteria.
---

# SDD Feature Workflow

## Phase 0 — Wireframe

Create or update `wireframes/<screen>.html` (self-contained HTML/CSS).

- Wizard steps, gallery, warning banners for error/invalid folders
- Desktop and mobile-width checks where relevant

**Stop for UX approval.**

## Phase 1 — Spec

Create or update `specs/<feature>/SPEC.md` with:

- Metadata (link wireframe path)
- Triggers & routing
- Visual & UI rules (aligned with wireframe)
- Acceptance criteria (Given/When/Then)
- Out of scope

**Stop for approval.**

## Phase 2 — Architecture

Add or update in `src/spacemaker/`:

- Domain entities / value objects
- Inbound port(s) for the use case
- Outbound port(s) as needed

**Stop for approval.**

## Phase 3 — Tests

Map each BDD scenario to pytest:

`test_given_…_when_…_then_…` with `# given` / `# when` / `# then`.

Target use cases and domain — not FastAPI routes in unit tests.

## Phase 4 — Implementation

Adapters and UI until tests pass. Update `memory/` at milestones (see `agent-memory` skill).

## Spec template

Follow structure in `docs/playbooks/spec-driven-development.md`. Conversion behavior must cite `docs/playbooks/SpaceMaker-adaptations.md`.
