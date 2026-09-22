# Spec-Driven Development (SpaceMaker)

Adapted from the GamesLibrary SDD playbook for Python + web UI.

## Philosophy

Spec → ports → tests → implementation. If implementation exposes a spec flaw, rewrite the spec first.

## SPEC.md location

`specs/<feature>/SPEC.md` at repo root (not under `docs/`).

## Anatomy

- **Metadata & dependencies** — links, related wireframe path
- **Triggers & routing** — how the user enters/exits the flow
- **Visual & UI rules** — must align with approved `wireframes/`
- **Acceptance criteria (BDD)** — Given/When/Then
- **Out of scope**

## Phase gates (see AGENTS.md)

0. Wireframe UX approval  
1. Spec approval  
2. Domain + ports approval  
3. Unit tests from BDD  
4. Adapters + implementation  

## Tests

pytest unit tests map each BDD scenario to `test_given_…_when_…_then_…`. UI automation is a later concern; wireframes validate layout before specs.

## Team workflow

Spec-only review before large implementation PRs. Repo `specs/` and `wireframes/` are truth.
