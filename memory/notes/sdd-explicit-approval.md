---
name: sdd-explicit-approval
description: design and spec need explicit chat approval; plans and todos are not approval
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

SDD: explicit design + spec approval before src.

- **Context:** Agents sometimes ran wireframe → spec → full implementation in one pass when the user attached a plan or said “implement the plan.”
- **Decision:** Phase gates in `AGENTS.md`, `sdd.mdc`, and `sdd-feature` skill require **explicit chat confirmation** after wireframe (design) and after spec before production source (`src/spacemaker/`, production static UI). Attached plans/todos are not substitutes for those approvals.
- **Rationale:** Keeps UX and behavioral truth in human-reviewed artifacts; reduces silent drift from wireframe/spec.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — SDD: explicit design + spec approval before src".
