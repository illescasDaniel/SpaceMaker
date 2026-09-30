# SpaceMaker — Agent Instructions

This repository uses **Spec-Driven Development (SDD)** and **Hexagonal Architecture**. Follow the Phase Gate Protocol for every feature or architectural change.

## Scale mindset

Despite the small current footprint, **always act as if this project will grow large.** Follow layer boundaries, ports, specs, wireframes, and tests even when a change feels trivial; prefer conventions and clear abstractions over one-off fixes that would not survive a bigger codebase.

## Hard rules

- Use **tabs** for indentation in Python and all project source files — not spaces.
- Hexagonal layering is mandatory: see `src/spacemaker/{domain,ports,application}` vs `adapters/` below, and the path-scoped rule (`.cursor/rules/hexagonal-python.mdc` / `.claude/rules/hexagonal-python.md`) for the full import guard and naming conventions.
- Never skip a Phase Gate. "Implement the plan" / "complete all todos" / an attached plan file / plan-mode approval is **not** design or spec approval — approval must be explicit, in chat.

## Phase Gate Protocol

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **0 — Design (wireframe)** | `wireframes/<screen>.html` (self-contained HTML/CSS) | **Stop.** Ask for UX/design approval. |
| **1 — Spec** | `specs/<feature>/SPEC.md` (agreed **Design decisions** — success criteria, failure handling, perf/resource budget, trust boundary — plus BDD, out of scope, aligned with wireframe) | **Stop.** Ask for spec approval. |
| **2 — Architecture** | Domain types and ports in `src/spacemaker/domain/`, `ports/` | **Stop.** Ask for approval before tests/adapters. |
| **3 — Tests** | Unit tests from BDD (`tests/unit/`); implementations may be stubs | Run tests; fix as needed. |
| **4 — Implementation** | Use cases, adapters, FastAPI/Web UI, desktop | Until tests pass. Must match approved wireframe unless spec is re-approved. |
| **5 — Grade** | Read-only `code-grader` subagent scores the branch against the spec | Automatic (no approval); fix FAILs, max 2 rounds, show scorecard. |

**One gate per explicit approval** — do not batch Phase 0→4 in one run, even if todos list all phases. After the wireframe, end the turn and wait. If Phase 4 reveals a spec flaw, rewrite the spec (Phase 1), get re-approval, then continue — don't patch around a bad spec.

Production source requiring prior approvals: `src/spacemaker/` (all layers) and `src/spacemaker/adapters/inbound/web/static/` (production HTML/JS/CSS). Allowed before spec approval: `wireframes/`, `specs/`, and `docs/`/`memory/` edits supporting the gate.

Full step-by-step workflow: `.cursor/skills/sdd-feature/SKILL.md` (mirrored at `.claude/skills/`).

## Memory bank

Per-branch project state lives in `memory/` (git-tracked, so it follows the branch). At session start, read `memory/activeContext.md` then `memory/progress.md`. Update on these triggers only:

- `memory/progress.md` — a task is completed, or a new task/bug is discovered.
- `memory/activeContext.md` — focus changes, a blocker is hit, or you're concluding work (log touched files, state, next step).
- `memory/decisions.md` — a significant technical/structural/dependency decision is made: append with context + decision + rationale (newest first, **never** rewrite history).

- `memory/friction/` — **an agent hits an error, a wrong/misleading/slow MCP result, a lying doc, or needs a workaround**: add one small `YYYY-MM-DD-slug.md` entry right then (template in `memory/friction/README.md`), then keep working. This is the backlog for improving the MCPs, docs and tooling.

Keep `activeContext.md` short — move finished threads to `memory/archive.md` rather than letting it accumulate. Never add worktree cleanup/deletion tasks to tracked memory (per-developer local hygiene, causes merge noise). Commit memory updates at milestones; don't leave the tree permanently dirty. Full protocol, branch-init steps, and merge guidance: `.cursor/skills/agent-memory/SKILL.md`.

## Orient before editing

Two tools exist so you don't need to read large swaths of the codebase up front — neither skips a Phase Gate.

- **Docs (the *why*):** read `docs/*.md` directly (`docs/index.md`, `docs/ARCHITECTURE.md`, `docs/testing.md`, `docs/agent-tooling.md`, `docs/playbooks/`). `uv run task docs-serve` is for humans browsing the rendered site, not for you.
- **`codenav` MCP (the *what calls what*):** for finding a symbol's definition, its usages, or its type — prefer the name-based tools (`symbol_info`, `outline`, `callers`, `implementations`), then drop to position tools (`search_symbol`, `definition`, `references`, `hover`, `diagnostics`) once you have a line. Backed by `ty`'s language server, so it resolves through real type inference (imports, dependency-injected parameters, dataclass fields, etc.) rather than text matching. Reserve **grep** for free-text / comments / specs / config keys (and anything MCP can't answer). See `docs/agent-tooling.md`.
- **`webnav` MCP (same idea, for JS/HTML/CSS):** same composites as `codenav` for JS/TS (`symbol_info`, `outline`, `callers`, `implementations`, plus position tools), for the project's web assets (`web/src/`, `src/spacemaker/adapters/inbound/web/static/`, `wireframes/`) — backed by TypeScript 7 `tsc --lsp --stdio` / `vscode-langservers-extracted`. Use `css_var` / `selector` for cross-file `--custom-properties` and `#id`/`.class` lookups. It is the npm package [`webnav-ts-mcp`](https://www.npmjs.com/package/webnav-ts-mcp) (own repo, `~/Projects/Code/Python/MCPs/webnav-ts-mcp`), launched with `npx`. See `docs/agent-tooling.md`.

**Example calls (copy these; prefer `name=` / `query=` as documented — each accepts the other as an alias):**

- `symbol_info(name="JobsMixin.start_convert")` — what is X, where is it used (Python)
- `symbol_info(name="renderGalleryItemStage")` — same for JS/TS
- `outline(file_path="web/src/gallery-item.ts")` — what's in this file
- `callers(name="start_convert")` — who calls this function
- `selector(name=".gallery-item-media")` — who uses this `#id`/`.class` (CSS + HTML + JS)

MCP tools are often deferred: fetch their schema (ToolSearch `select:`) before the first call. **When delegating to a subagent, paste one concrete example call into its prompt** — a single failed guess makes agents abandon the tool for grep.

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

## Worktree dependencies

In a linked worktree (any `git worktree list` entry after the first), `.venv`/`node_modules` may be missing or stale. **Before the first quality-gate run, execute `bash .cursor/skills/new-worktree/scripts/copy-venv.sh`** — it is safe to run directly (only the `/new-worktree` *skill* is user-invoked), is a no-op when everything is current, copies from the primary checkout when lockfiles match, and re-syncs (`uv sync` / `npm ci`) when they don't. To *create* a worktree, follow the `/new-worktree` skill's steps rather than a bare `git worktree add` / `EnterWorktree`.

## Quality gate

Requires [uv](https://docs.astral.sh/uv/). Python: **ruff**, **ty**, **pytest** via `uv run task checks` ([scripts/quality/checks.py](scripts/quality/checks.py), mirrored by [checks.sh](scripts/quality/checks.sh)). Web JS/HTML/TS: **Biome** + `tsc` via `npm ci && npm run check` (also run by the quality gate).

## Rules — Cursor vs Claude Code

Both tools read this file natively. Always-on guidance stays here; anything that should load only for a specific area (e.g. hexagonal layout) is a **path-scoped rule**, hand-maintained as an equivalent pair: `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md`. The two directories are checked for drift by `tests/unit/test_agent_context.py`. Maintenance details (formats, why not symlinks): `docs/agent-tooling.md`.

## Skills

Project workflows: `.cursor/skills/{sdd-feature,agent-memory,fast-tests}/`, mirrored at `.claude/skills/` via a symlink. User-invoked only: `/save-changes`, `/save-pr-changes`, `/apply-worktree`, `/delete-worktree`, `/new-worktree`.

Subagents: `code-grader` (Phase 5) lives as a hand-maintained pair, `.cursor/agents/code-grader.md` and `.claude/agents/code-grader.md` (host-specific frontmatter, identical body).

## Source of truth

`specs/` holds feature specifications. `wireframes/` holds UX layout truth before specs. `memory/` holds per-branch agent state. External trackers track work; the repo tracks truth.
