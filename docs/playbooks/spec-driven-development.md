# Spec-Driven Development (SpaceMaker)

Adapted from the GamesLibrary SDD playbook for Python + web UI.

## Philosophy

Spec → ports → tests → implementation. If implementation exposes a spec flaw, rewrite the spec first.

## SPEC.md location

`specs/<feature>/SPEC.md` at repo root (not under `docs/`).

## Anatomy

- **Metadata & dependencies** — links, related wireframe and/or `design/<feature>/DESIGN.md` path
- **Design decisions** — success criteria, failure handling, performance & resource budget, trust boundary, compatibility & rollout (see below)
- **Triggers & routing** — how the user enters/exits the flow
- **Visual & UI rules** — must align with approved `wireframes/`
- **Acceptance criteria (BDD)** — Given/When/Then
- **Out of scope**

## Design decisions

A useful design document pins five decisions (idea from an Anthropic partner course). Agree them with the user at the start of Phase 1, before writing the spec body; they are approved together with the spec. Each is answered or marked `N/A — <reason>`.

| Decision | SpaceMaker meaning | Traces to |
|---|---|---|
| **Success criteria** | Observable "done" beyond the BDD list: user outcome, measurable thresholds (no data loss, idempotent re-run) | BDD scenarios / tests |
| **Failure handling** | What fails, what the user sees, retry/skip/quarantine (`error/`, `invalid/`), partial state and resume | error/warning scenarios, banners |
| **Performance & resource budget** | Latency/throughput, disk/CPU/GPU/memory, size limits, network cost | fast-tests, perf-related tests |
| **Trust boundary** | Untrusted input (device paths, upload filenames, LAN clients on `/share` `/transfer`, subprocess args), what is trusted, what may touch FS/network. Validate at inbound adapters/application, never assume in domain | path-traversal / auth scenarios |
| **Compatibility & rollout** | Who depends on what changes (API clients, stored data such as library folders and settings files, older app versions), versioning, migration order, feature flag, rollback. Missing only warns in the pre-checks, so older specs keep passing | migration / old-data scenarios |

Every failure-handling and trust-boundary decision needs at least one BDD scenario, and so does every `F<n>` failure branch of the system design (put the id in the scenario title, e.g. `### Scenario: export already running (F1)`). Existing specs adopt the section when next touched (no bulk retrofit).

## Phase gates (see AGENTS.md)

Each gate needs **explicit human confirmation in chat** before the next phase. **Plan approval, plan-mode OK, attached plans, and todo lists do not replace design or spec approval.**

### Implement-the-plan rule

When execution starts after a plan is approved:

1. **First turn:** design only (wireframe, `DESIGN.md`, or both) → user reviews it → **wait** for “design approved” (or change requests).
2. **Next turns:** one gate at a time (spec → architecture → tests/implementation).

Never batch all phases because the user said “implement the plan” or “complete all todos”.

0. **Design** — UI track: wireframe in `wireframes/`; system track: `design/<feature>/DESIGN.md` (Mermaid; failure branches labelled `F1`, `F2`, …; run `design_preview.py --check`); fullstack: both, one gate → **end turn**; UX/design approval required  
1. **Spec** — `specs/<feature>/SPEC.md` → stop for spec approval (no `src/` or production UI yet)  
2. **Architecture** — domain + ports → stop for approval  
3. **Tests** — unit tests from BDD  
4. **Implementation** — adapters + production UI until green; must match the **approved** wireframe and `DESIGN.md`  
5. **Grade** — read-only `code-grader` subagent scores the branch against the spec (see `docs/agent-tooling.md`); no approval gate, fix FAILs (max 2 rounds), show the scorecard  

If layout or behavior changes during implementation, update wireframe, design and/or spec and **re-approve** before continuing.

## Tests

pytest unit tests map each BDD scenario to `test_given_…_when_…_then_…`. UI automation is a later concern; wireframes validate layout before specs.

## Team workflow

Spec-only review before large implementation PRs. Repo `specs/`, `wireframes/` and `design/` are truth.
