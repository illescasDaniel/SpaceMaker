# SpaceMaker — Agent Instructions

This repository uses **Spec-Driven Development (SDD)** and **Hexagonal Architecture**. Follow the Phase Gate Protocol for every feature or architectural change.

## Agents and delegation

You are the orchestrator: delegate to the `architect`, `coder`, `coder-small`, `code-reviewer`, `code-grader` and `utility`
subagents in `.claude/agents/`, `.cursor/agents/` or `.codex/agents/` for the current tool, and own every approval gate and
memory write. Read `.agents/development-workflow.md` for routing and briefs, and `.agents/delegation-tiers.md` for tiers.

## Python code goes to `coder-python` or `coder-python-small`

Any task that adds, changes, renames, moves or deletes `.py`/`.pyi` code goes to `coder-python` or `coder-python-small`, not the generic
`coder`: it uses the project's `codenav` MCP for type-checked navigation and refactoring. Keep `coder` for everything
else, and split a task that spans languages.

## TypeScript code goes to `coder-typescript` or `coder-typescript-small`

Any task that adds, changes, renames, moves or deletes JavaScript/TypeScript/HTML/CSS (`.ts`, `.tsx`, `.js`, `.jsx`,
`.html`, `.css`) code goes to `coder-typescript` or `coder-typescript-small`, not the generic `coder`: it uses the project's `webnav` MCP for
type-checked navigation and refactoring. Keep `coder` for everything else, and split a task that spans languages.

## Scale mindset

Despite the small current footprint, **always act as if this project will grow large.** Follow layer boundaries, ports, specs, wireframes, and tests even when a change feels trivial; prefer conventions and clear abstractions over one-off fixes that would not survive a bigger codebase.

## Hard rules

- Use **tabs** for indentation in Python and all project source files — not spaces.
- Hexagonal layering is mandatory: see `src/spacemaker/{domain,ports,application}` vs `adapters/` below, and the path-scoped rule (`.cursor/rules/hexagonal-python.mdc` / `.claude/rules/hexagonal-python.md`) for the full import guard and naming conventions.
- Never skip a Phase Gate. "Implement the plan" / "complete all todos" / an attached plan file / plan-mode approval / a page checkbox is **not** design, spec or architecture approval — approval must be explicit, in chat.

## Phase Gate Protocol (Spec-Driven Development)

Use the `sdd-html-feature` skill for every feature or architectural change: one page `sdd/<feature>.html` holds the
Design, Spec, Architecture, Build, Verify and Approvals tabs. Stop for **separate design, spec and architecture approvals
in chat** and resume at the first unapproved gate; after the build, QA and the `code-grader` run automatically unless the
user opts out at the architecture gate. Details: `.agents/loadout-guidance.md` and the skill.

- SpaceMaker specifics: the Design tab covers the UI (self-contained HTML/CSS) and the system design (flows, `F<n>`
  failure branches, data, contracts); the Spec tab keeps the five design decisions (success criteria, failure handling,
  perf/resource budget, trust boundary, compatibility & rollout) and a scenario per `F<n>`; the Architecture gate is the
  domain types and ports in `src/spacemaker/domain/` and `ports/`; tests follow the `fast-tests` skill.
- **One gate per explicit approval**: do not batch gates, even if todos list them all. Production source requiring prior
  approvals: `src/spacemaker/` (all layers) and `src/spacemaker/adapters/inbound/web/static/` (production HTML/JS/CSS);
  allowed before spec approval: `sdd/`, legacy `specs/`, `wireframes/`, `design/`, and `docs/`/`memory/` edits supporting the gate. For changes under `src/spacemaker/`, read `.claude/rules/hexagonal-python.md` first (Codex must load it explicitly).
- Legacy features: those specified before 2026-11-17 keep `specs/<feature>/SPEC.md`, `wireframes/` and
  `design/<feature>/DESIGN.md` as their historical record (old workflow: the `sdd-feature` skill). Finish an in-flight
  legacy feature in that format; start new features as pages. Never delete or rewrite those files to migrate them.

## Project memory (memory-1)

Use the `memory-1` skill: at session start read `memory/NOW.md` (check it against git) and `memory/MEMORY.md`; save
decisions, reversals, preferences and incidents as one-fact notes in `memory/notes/`. Full protocol and end-of-session
steps: `.agents/loadout-guidance.md`. Keep the `memory/friction/` practice for tooling errors and workarounds. The old
bank (`activeContext.md`, `progress.md`, `decisions.md`, `archive.md`), `.agemem/` and the jevmem notes were migrated
into `memory/notes/` and `memory/topics/` on 2026-11-17 and are kept as history: do not delete them without the user's yes.

## Project docs (docs-1)

Start at `docs-index/INDEX.md` (one line per doc; IDs `DOC-n`). It lives outside `docs/` because `docs/index.md` is the
MkDocs home page: run `docs_index.py --docs docs-index write|check`. Details: `.agents/loadout-guidance.md`.

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
| Feature design, spec, architecture and approvals | `sdd/<feature>.html` (legacy: `specs/<feature>/SPEC.md`, `wireframes/<screen>.html`, `design/<feature>/DESIGN.md`) |
| Conversion policy, library folders, desktop shell | `docs/playbooks/SpaceMaker-adaptations.md` |
| System design, entry points, routing, persistence | `docs/ARCHITECTURE.md` |
| SDD philosophy, hexagonal ports/adapters, test conventions | `docs/playbooks/{spec-driven-development,hexagonal-architecture,fast-tests}.md` |
| Packaging (portable builds, bundled CLIs, legal) | `specs/packaging/SPEC.md`, `docs/legal/` |

**Priority when docs conflict:** the feature's page (or legacy `SPEC.md`) → `docs/playbooks/SpaceMaker-adaptations.md` → `.claude/rules/` (and `.cursor/rules/`) → playbooks → generic examples in playbooks.

## Worktree dependencies

In a linked worktree (any `git worktree list` entry after the first), `.venv`/`node_modules` may be missing or stale. **Before the first quality-gate run, execute `bash .cursor/skills/new-worktree/scripts/copy-venv.sh`** — it is safe to run directly (only the `/new-worktree` *skill* is user-invoked), is a no-op when everything is current, copies from the primary checkout when lockfiles match, and re-syncs (`uv sync` / `npm ci`) when they don't. To *create* a worktree, follow the `/new-worktree` skill's steps rather than a bare `git worktree add` / `EnterWorktree`.

## Quality gate

Requires [uv](https://docs.astral.sh/uv/). Python: **ruff**, **ty**, **pytest** via `uv run task checks` ([scripts/quality/checks.py](scripts/quality/checks.py), mirrored by [checks.sh](scripts/quality/checks.sh)). Web JS/HTML/TS: **Biome** + `tsc` via `npm ci && npm run check` (also run by the quality gate). The gate ends with a dependency audit (`pip-audit` on the locked deps + `npm audit --audit-level=high`; needs network, skip offline with `--skip-audit`); Dependabot (`.github/dependabot.yml`) opens weekly update PRs.

## Rules — Claude Code, Cursor and Codex

Cursor and Codex read this file natively; Claude Code imports it through `CLAUDE.md`. Always-on guidance stays here; anything that should load only for a specific area (e.g. hexagonal layout) is a **path-scoped rule**, hand-maintained as an equivalent pair: `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md`. The two directories are checked for drift by `tests/unit/test_agent_context.py`. Maintenance details (formats, why not symlinks): `docs/agent-tooling.md`.

## Skills

Project workflows: `.cursor/skills/{sdd-html-feature,memory-1,docs-1,worktree,fast-tests}/`, mirrored at `.claude/skills/` via a symlink; `sdd-feature`, `agent-memory` and `jev-memory` are kept for legacy features and history only. User-invoked only: `/save-changes`, `/save-pr-changes`, `/apply-worktree`, `/delete-worktree`, `/new-worktree`.

Subagents from agentic-loadout 0.8.0 (originally [agent-guild](https://github.com/illescasDaniel/agent-guild)) live in `.claude/agents/`, `.cursor/agents/` and `.codex/agents/` (native formats). Preserve the SpaceMaker `code-grader` body on all three tools; Claude/Cursor metadata is checked by `tests/unit/test_agent_context.py`. Codex skills share `.cursor/skills/` through `.agents/skills`; `.codex/skills` is a compatibility link.

## Source of truth

`sdd/` holds feature pages (design, spec, architecture, approvals); `specs/`, `wireframes/` and `design/` hold the legacy features' records. `memory/` holds per-branch agent memory. External trackers track work; the repo tracks truth.

## Agentic-loadout workflow

Read `.agents/loadout-guidance.md` for the managed Entire, memory, docs, SDD and worktree guidance (agentic-loadout 0.8.0);
the project-specific rules above take precedence.

## Isolated worktrees

Use `/new-worktree` when the user asks or agrees (ask once if the checkout has changes you did not make). Setup
for a new worktree: "Worktree dependencies" above; details in `.agents/loadout-guidance.md`.

## Entire session history

Entire is enabled; follow `.agents/loadout-guidance.md` for checkpoint use and session export.
