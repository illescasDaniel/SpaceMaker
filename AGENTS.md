# SpaceMaker — Agent Instructions

This repository uses **Spec-Driven Development (SDD)** and **Hexagonal Architecture**. Follow the Phase Gate Protocol for every feature or architectural change.

## Scale mindset

Despite the small current footprint, **always act as if this project will grow large.** Follow layer boundaries, ports, specs, wireframes, and tests even when a change feels trivial; prefer conventions and clear abstractions over one-off fixes that would not survive a bigger codebase.

## Hard rules

- Use **tabs** for indentation in Python and all project source files — not spaces.
- Hexagonal layering is mandatory: see `src/spacemaker/domain/ports/application` vs `adapters/` below, and the path-scoped rule (`.cursor/rules/hexagonal-python.mdc` / `.claude/rules/hexagonal-python.md`) for the full import guard and naming conventions.
- Never skip a Phase Gate. "Implement the plan" / "complete all todos" / an attached plan file / plan-mode approval is **not** design or spec approval — approval must be explicit, in chat.

## Phase Gate Protocol

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **0 — Design (wireframe)** | `wireframes/<screen>.html` (self-contained HTML/CSS) | **Stop.** Ask for UX/design approval. |
| **1 — Spec** | `specs/<feature>/SPEC.md` (BDD, out of scope, aligned with wireframe) | **Stop.** Ask for spec approval. |
| **2 — Architecture** | Domain types and ports in `src/spacemaker/domain/`, `ports/` | **Stop.** Ask for approval before tests/adapters. |
| **3 — Tests** | Unit tests from BDD (`tests/unit/`); implementations may be stubs | Run tests; fix as needed. |
| **4 — Implementation** | Use cases, adapters, FastAPI/Web UI, desktop | Until tests pass. Must match approved wireframe unless spec is re-approved. |

**One gate per explicit approval** — do not batch Phase 0→4 in one run, even if todos list all phases. After the wireframe, end the turn and wait. If Phase 4 reveals a spec flaw, rewrite the spec (Phase 1), get re-approval, then continue — don't patch around a bad spec.

Production source requiring prior approvals: `src/spacemaker/` (all layers) and `src/spacemaker/adapters/inbound/web/static/` (production HTML/JS/CSS). Allowed before spec approval: `wireframes/`, `specs/`, and `docs/`/`memory/` edits supporting the gate.

Full step-by-step workflow: `.cursor/skills/sdd-feature/SKILL.md` (mirrored at `.claude/skills/`).

## Memory bank

Per-branch project state lives in `memory/` (git-tracked, so it follows the branch). At session start, read `memory/activeContext.md` then `memory/progress.md`. Update on these triggers only:

- `memory/progress.md` — a task is completed, or a new task/bug is discovered.
- `memory/activeContext.md` — focus changes, a blocker is hit, or you're concluding work (log touched files, state, next step).
- `memory/decisions.md` — a significant technical/structural/dependency decision is made: append with context + decision + rationale (newest first, **never** rewrite history).

Keep `activeContext.md` short — move finished threads to `memory/archive.md` rather than letting it accumulate. Never add worktree cleanup/deletion tasks to tracked memory (per-developer local hygiene, causes merge noise). Commit memory updates at milestones; don't leave the tree permanently dirty. Full protocol, branch-init steps, and merge guidance: `.cursor/skills/agent-memory/SKILL.md`.

## Orient before editing

Two tools exist so you don't need to read large swaths of the codebase up front — neither skips a Phase Gate.

- **Docs (the *why*):** read `docs/*.md` directly (`docs/index.md`, `docs/ARCHITECTURE.md`, `docs/testing.md`, `docs/agent-tooling.md`, `docs/playbooks/`). `uv run task docs-serve` is for humans browsing the rendered site, not for you.
- **`codenav` MCP (the *what calls what*):** for finding a symbol's definition, its usages, or its type — use the `codenav` MCP tools (`search_symbol`, `definition`, `references`, `hover`, `diagnostics`) instead of grepping. It's backed by `ty`'s language server, so it resolves through real type inference (imports, dependency-injected parameters, dataclass fields, etc.) rather than text matching, and is faster and more deterministic than a broad grep for this kind of lookup. Reserve grep for things codenav can't answer (free-text search across comments/strings/config). See `docs/agent-tooling.md` for why it's a purpose-built server rather than a generic LSP bridge.

## Where to look

| Question | Source |
|---|---|
| Feature behavior (BDD) | `specs/<feature>/SPEC.md` |
| UX layout | `wireframes/<screen>.html` |
| Conversion policy, library folders, desktop shell | `docs/playbooks/SpaceMaker-adaptations.md` |
| System design, entry points, routing, persistence | `docs/ARCHITECTURE.md` |
| SDD philosophy, hexagonal ports/adapters, test conventions | `docs/playbooks/{spec-driven-development,hexagonal-architecture,fast-tests}.md` |
| Packaging (portable builds, bundled CLIs, legal) | `specs/packaging/SPEC.md`, `docs/legal/` |

**Priority when docs conflict:** `specs/<feature>/SPEC.md` → `docs/playbooks/SpaceMaker-adaptations.md` → `.claude/rules/` (and `.cursor/rules/`) → playbooks → generic examples in playbooks.

## Quality gate

Requires [uv](https://docs.astral.sh/uv/). Python: **ruff**, **ty**, **pytest** via `uv run task checks` ([scripts/quality/checks.sh](scripts/quality/checks.sh)). Web JS/HTML: **Biome** via `npm ci && npm run check`.

## Rules — Cursor vs Claude Code

Both tools read this file natively. Always-on guidance stays here; anything that should load only for a specific area (e.g. hexagonal layout) is a **path-scoped rule**, hand-maintained as an equivalent pair: `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md`. The two directories are checked for drift by `tests/unit/test_agent_context.py`. Maintenance details (formats, why not symlinks): `docs/agent-tooling.md`.

## Skills

Project workflows: `.cursor/skills/{sdd-feature,agent-memory,fast-tests}/`, mirrored at `.claude/skills/` via a symlink. User-invoked only: `/save-changes`, `/apply-worktree`, `/delete-worktree`.

## Source of truth

`specs/` holds feature specifications. `wireframes/` holds UX layout truth before specs. `memory/` holds per-branch agent state. External trackers track work; the repo tracks truth.
