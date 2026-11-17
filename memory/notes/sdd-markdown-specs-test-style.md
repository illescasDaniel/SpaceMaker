---
name: sdd-markdown-specs-test-style
description: Markdown specs in specs/<feature>/SPEC.md, wireframes first, given/when/then tests
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: sdd-html-feature-pages
source:
---

SDD, wireframes, and test style.

- **Context:** Greenfield SpaceMaker; user referenced GamesLibrary SDD and srxy tests.
- **Decision:** Markdown specs in `specs/<feature>/SPEC.md` (not Cucumber `.feature` files). Wireframes in `wireframes/` before specs. pytest with `test_given_…_when_…_then_…` naming and `# given` / `# when` / `# then` bodies (srxy style).
- **Rationale:** Matches existing agent workflows; keeps UX and behavior review separate; fast unit tests without Gherkin tooling.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — SDD, wireframes, and test style".

Superseded by [sdd-html-feature-pages](sdd-html-feature-pages.md).
