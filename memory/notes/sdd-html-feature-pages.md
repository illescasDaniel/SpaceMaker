---
name: sdd-html-feature-pages
description: new features use one sdd/<feature>.html page per feature; legacy specs/, wireframes/, design/ kept untouched
type: decision
date: 2026-11-17
status: current
supersedes: sdd-markdown-specs-test-style
superseded_by:
source:
---

From 2026-11-17 every feature or architectural change uses the `sdd-html-feature` skill: one page `sdd/<feature>.html` with Design, Spec, Architecture, Build, Verify and Approvals tabs, with separate design, spec and architecture approvals in chat. Features specified before that date keep `specs/<feature>/SPEC.md`, `wireframes/` and `design/<feature>/DESIGN.md` as their record; an in-flight legacy feature is finished in that format.

**Rejected:** migrating the legacy records into pages.
**How to apply:** never delete or rewrite the legacy spec files to migrate them (AGENTS.md).
