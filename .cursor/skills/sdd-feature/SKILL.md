---
name: sdd-feature
description: Run Spec-Driven Development for SpaceMaker features. Use when adding or changing user-facing flows, wireframes, SPEC.md, or implementing from acceptance criteria.
---

# SDD Feature Workflow

## Mandatory gates (explicit human confirmation)

Do **not** skip or batch gates. After each gate deliverable, **stop the turn** and ask the user to approve before the next phase.

| User says | Agent may do |
|-----------|----------------|
| “Add feature X” / “implement the plan” / plan mode OK / “complete all todos” | **Phase 0 only** (wireframe), then **end turn** for **design approval** |
| User approves wireframe / design (explicit in chat) | Phase 1 only (spec), then stop for **spec approval** |
| User approves spec | Phase 2 (ports/domain), then stop for **architecture approval** |
| User approves architecture | Phases 3–4 (tests, then adapters + production UI) |

An attached plan file, plan-mode approval, or todo list is **not** wireframe or spec approval. The user must confirm design and spec in chat (e.g. “wireframe LGTM”, “wireframe approved”, “spec approved”).

### Anti-patterns (never do this)

- Implementing specs, `src/`, or production `static/` in the **same turn** as the first wireframe drop.
- Treating “implement the plan” as permission to run Phase 0–4 back-to-back.
- Skipping the browser-review pause — always tell the user **when** to open `wireframes/…` and **wait** for their reply.

### Wireframe hand-off (required text)

After saving the wireframe, include:

- Path: `wireframes/<file>.html`
- Command: `xdg-open wireframes/<file>.html` (or full path)
- Ask: explicit approval before spec or code

**Forbidden before spec approval:** changes under `src/spacemaker/` or production `static/` except as part of an already-approved spec (refactors must keep specs green or update spec + re-approve).

## Phase 0 — Wireframe (design)

Create or update `wireframes/<screen>.html` (self-contained HTML/CSS).

- Wizard steps, gallery, warning banners for error/invalid folders
- Desktop and mobile-width checks where relevant

**Stop. End the turn.** Do not start Phase 1 in the same session turn unless the user already wrote explicit wireframe approval above.

Ask: “Please review the wireframe at … — reply with wireframe approved (or requested changes) before I write the spec or touch production UI.”

## Phase 1 — Spec

**Step 1 — Agree the four design decisions (before writing the spec body).** Draft a proposed answer for each, then ask the user to confirm or adjust (chat or AskUserQuestion). Do not silently invent them. Each must be answered or marked `N/A — <reason>`; empty is not allowed.

| Decision | Pin down |
|----------|----------|
| Success criteria | Observable "done" beyond the BDD list: user outcome, measurable thresholds (no data loss, idempotent re-run) |
| Failure handling | What can fail, what the user sees, retry / skip / quarantine (`error/`, `invalid/`), partial state and resume |
| Performance & resource budget | Latency/throughput targets, disk/CPU/GPU/memory, size limits, network cost (e.g. CLI downloads) |
| Trust boundary | Untrusted input (device paths, upload filenames, LAN clients, subprocess args), what is trusted, what may touch FS/network; validated at inbound adapters |

**Step 2 — Write** `specs/<feature>/SPEC.md` with:

- Metadata (link wireframe path)
- `## Design decisions` (the four above, right after Metadata)
- Triggers & routing
- Visual & UI rules (aligned with wireframe)
- Acceptance criteria (Given/When/Then) — every failure-handling and trust-boundary decision needs at least one scenario
- Out of scope

**Stop.** Ask: “Please review `specs/<feature>/SPEC.md` (including Design decisions) — approve so I can add ports and implementation?”

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

Follow structure in `docs/playbooks/spec-driven-development.md` (including `## Design decisions`). Conversion behavior must cite `docs/playbooks/SpaceMaker-adaptations.md`.
