---
name: graphify-feedback-loop
description: Graphify save-result/reflect loop adopted; diagnose multigraph trigger-based
type: decision
date: 2026-09-24
status: superseded
supersedes:
superseded_by: graphify-removed-codenav-renamed
source:
---

Graphify feedback loop (`save-result`/`reflect`) adopted; `diagnose multigraph` documented as trigger-based, not routine.

- **Context:** Walked through Graphify's less-obvious CLI surface (`diagnose multigraph`, `save-result`, `reflect`) on request, to decide whether they're worth using and, if so, to write that into `AGENTS.md` so future sessions pick it up without being re-asked.
- **Decision:** (1) `graphify diagnose multigraph` is documented as a trigger-based check (after a big refactor, or when a graph query result looks suspicious), not a per-task step — ran once against the live graph as a baseline: 0 collapsed edges, 0 dangling endpoints. (2) The `save-result`/`reflect` feedback loop is adopted: after a graph query that actually informed a real decision, tag its outcome (`useful`/`dead_end`/`corrected`); `reflect` deterministically aggregates tags into `graphify-out/reflections/LESSONS.md`. (3) `.gitignore` now un-ignores `graphify-out/memory/*.md` and `graphify-out/reflections/LESSONS.md` (previously blanket-ignored under `graphify-out/*`) so this signal persists across sessions/branches instead of resetting per clone/worktree, mirroring how `graph.json`/`GRAPH_REPORT.md` are already tracked.
- **Rationale:** No LLM cost — `save-result`/`reflect` are pure bookkeeping over outcomes I tag myself, so the marginal cost of adopting it is just discipline, not tokens or an API key. Untracked (gitignored) would have meant the accumulating "which graph nodes are actually reliable" signal lived only on one machine and vanished on every fresh clone, defeating the point of a cross-session feedback loop — same reasoning that already justifies tracking `memory/decisions.md` itself. `LESSONS.md` is explicitly *not* a replacement for `decisions.md`: it's auto-generated per-symbol reliability signal, not a hand-written per-decision narrative — both stay, documented side by side in `AGENTS.md`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — Graphify feedback loop (`save-result`/`reflect`) adopted; `diagnose multigraph` documented as trigger-based, not routine".

Superseded by [graphify-removed-codenav-renamed](graphify-removed-codenav-renamed.md).
