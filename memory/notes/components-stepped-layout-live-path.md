---
name: components-stepped-layout-live-path
description: Components probes host PATH live for display; convert stays gated until Continue
type: decision
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

Components stepped layout + live PATH before Continue.

- **Context:** After brew install hints, Components still looked “broken” until Continue, and PATH rows were amber; users install tools while the screen is open.
- **Decision:** Status always probes host PATH for display (`resolution=path` green). Convert stays gated until Continue. Aggregate `summary_status` ok|warning|missing; optional PM + bulk install commands; Details `details_expanded`; UI polls ~3s while Components active. Continue calls `ensure_host_tool_path_dirs` then allows PATH fallback.
- **Rationale:** Matches approved wireframe/spec; keeps first-run trust gate without hiding brew tools that are already installed.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — Components stepped layout + live PATH before Continue".
