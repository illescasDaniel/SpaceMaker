---
name: home-hub-3-column-tiles
description: Home hub is a 3-column grid of 4:3 tiles with a floating footer
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

Home hub: 3-column 4:3 tiles + floating footer (UI-only).

- **Context:** User wanted a denser Home with three columns, smaller tiles that stay 4:3 (not square), unchanged icon/title size, and a floating Settings/About footer instead of a full-width strip. Also asked to drop hub lead copy and to separate wireframe Tip vs agent/reviewer notes so production never inherits programmer chrome.
- **Decision:** Spec/wireframe updated under SDD gates; architecture is inbound-static-only (no domain/ports). Production `index.html` matches: `repeat(3, …8.75rem)`, `aspect-ratio: 4 / 3`, fixed floating `.app-footer`, no `.home-hub-lead`. Wireframe annotation vocabulary (`.tip` / `.wf-note` / `.wf-demo`) documented in `wireframes/README.md` and never copied to `static/`. Bumped `UI_SHELL_VERSION` to `2026.09.home-layout`.
- **Rationale:** Layout chrome doesn’t need hexagonal surface area; stamping + shell version bump keeps desktop WebEngine on the new CSS.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — Home hub: 3-column 4:3 tiles + floating footer (UI-only)".
