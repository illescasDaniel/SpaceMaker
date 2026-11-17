---
name: sdd-phase5-code-grader
description: independent read-only code-grader after the build, max 2 fix rounds, plus mechanical pre-checks
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

SDD Phase 5: independent `code-grader` subagent + mechanical pre-check script.

- **Context:** User read about "code grading" (LLM-as-judge) and asked to run it after the `sdd-feature` implementation phase. Chose: subagent (not more tests) with all read-only tools incl. `codenav`/`webnav`; Claude and Cursor each get their own agent file (copy with host-specific syntax, not symlink); mechanical-check script only if reliable.
- **Decision:** Added Phase 5 to `sdd-feature`: after Phase 4 is green, spawn `code-grader` (`.claude/agents/`, `.cursor/agents/`, identical bodies, drift-tested), fix FAILs (max 2 rounds), show scorecard. Automatic, not an approval gate (read-only). `scripts/quality/grade_prechecks.py` (`uv run task grade-prechecks`) does layering / new-test naming / SPEC structure. Layering hard-fails only on branch-touched files (found 3 pre-existing `application → bootstrap` imports in `managed_tools.py`, warned, not fixed). Scenario→test name matching was tested and **dropped** as too noisy (~60% false "uncovered" on the gallery spec).
- **Rationale:** A fresh-context reviewer avoids self-grading leniency; the spec is already the rubric. Deterministic checks stay deterministic; judgement stays with the grader.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — SDD Phase 5: independent `code-grader` subagent + mechanical pre-check script".
