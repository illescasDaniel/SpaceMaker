---
name: spec-design-decisions-section
description: every spec answers success criteria, failure handling, perf budget and trust boundary up front
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

SPEC.md carries four agreed "Design decisions" (success criteria, failure handling, perf/resource budget, trust boundary).

- **Context:** User read that a useful design doc pins four decisions (success criteria, failure handling, cost/latency budget, trust boundary) and asked to adopt them for SDD, established together per feature. SpaceMaker specs covered these only implicitly and inconsistently.
- **Decision:** Add a `## Design decisions` section after Metadata in every new/changed `SPEC.md`. The agent drafts, the user confirms at the start of Phase 1 (before the spec body); approved with the spec (no new gate). Each item answered or `N/A — <reason>`; failure-handling and trust-boundary items need a BDD scenario. "Cost/latency" is adapted to "performance & resource budget" (local app). Updated `sdd-feature` skill, SDD playbook, hexagonal playbook, `AGENTS.md`, `specs/README.md`. Existing specs adopt it when next touched; no enforcement test yet.
- **Rationale:** Cheapest place (specs are truth, gate exists); forces the hard questions before code without a second doc to drift.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — SPEC.md carries four agreed "Design decisions" (success criteria, failure handling, perf/resource budget, trust boundary)".
