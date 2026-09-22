---
name: sdd-feature
description: Run Spec-Driven Development for SpaceMaker features. Use when adding or changing user-facing flows, wireframes, SPEC.md, or implementing from acceptance criteria.
---

# SDD Feature Workflow

## Mandatory gates (explicit human confirmation)

Do **not** skip or batch gates. After each gate deliverable, **stop the turn** and ask the user to approve before the next phase.

| User says | Agent may do |
|-----------|----------------|
| “Add feature X” / “implement the plan” | Phase 0 only (wireframe), then stop for **design approval** |
| User approves wireframe / design | Phase 1 only (spec), then stop for **spec approval** |
| User approves spec | Phase 2 (ports/domain), then stop for **architecture approval** |
| User approves architecture | Phases 3–4 (tests, then adapters + production UI) |

An attached plan file or todo list is **not** wireframe or spec approval. The user must confirm design and spec in chat (e.g. “wireframe LGTM”, “spec approved”).

**Forbidden before spec approval:** changes under `src/spacemaker/` or production `static/` except as part of an already-approved spec (refactors must keep specs green or update spec + re-approve).

## Phase 0 — Wireframe (design)

Create or update `wireframes/<screen>.html` (self-contained HTML/CSS).

- Wizard steps, gallery, warning banners for error/invalid folders
- Desktop and mobile-width checks where relevant

**Stop.** Ask: “Please review the wireframe at … — approve design so I can write the spec?”

## Phase 1 — Spec

Create or update `specs/<feature>/SPEC.md` with:

- Metadata (link wireframe path)
- Triggers & routing
- Visual & UI rules (aligned with wireframe)
- Acceptance criteria (Given/When/Then)
- Out of scope

**Stop.** Ask: “Please review `specs/<feature>/SPEC.md` — approve so I can add ports and implementation?”

## Phase 2 — Architecture

Add or update in `src/spacemaker/`:

- Domain entities / value objects
- Inbound port(s) for the use case
- Outbound port(s) as needed

**Stop for architecture approval** before Phase 3.

## Phase 3 — Tests

Map each BDD scenario to pytest:

`test_given_…_when_…_then_…` with `# given` / `# when` / `# then`.

Target use cases and domain — not FastAPI routes in unit tests.

## Phase 4 — Implementation

Adapters and production UI until tests pass. Update `memory/` at milestones (see `agent-memory` skill).

## Spec template

Follow structure in `docs/playbooks/spec-driven-development.md`. Conversion behavior must cite `docs/playbooks/SpaceMaker-adaptations.md`.
