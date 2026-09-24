# SpaceMaker — Agent Instructions

This repository uses **Spec-Driven Development (SDD)** and **Hexagonal Architecture**. Follow the Phase Gate Protocol for every feature or architectural change.

## Scale mindset

Despite the small current footprint, **always act as if this project will grow large.** Small, medium, and larger decisions alike should assume future scale — do not take shortcuts that would block that growth.

- Follow layer boundaries, ports, specs, wireframes, and tests even when a change feels trivial.
- Prefer conventions and clear abstractions over one-off fixes that would not survive a bigger codebase.
- When choosing between options, pick the one that stays correct as features, files, and contributors multiply.

## Memory bank

Per-branch project state lives in `memory/` (git-tracked). Always-on rule: `.cursor/rules/agent-memory.mdc`.

1. **Session start:** read `memory/activeContext.md`, then `memory/progress.md`.
2. **During work:** update those files only on the triggers in the rule; append significant choices to `memory/decisions.md` (newest first, never rewrite history).
3. **Hand-off:** before finishing a session with progress, leave `activeContext.md` as the next prompt's starting point.

How the files work and how to reset them on a new branch: [memory/README.md](memory/README.md).

## Phase Gate Protocol

Follow phases in order. **Each phase gate** requires **explicit human confirmation in chat** before the next phase — do not infer approval from a broad “implement the plan” message, from an attached plan file alone, from **plan mode OK**, from **“complete all todos”**, or from continuing the same thread.

### “Implement the plan” does not skip gates

When the user approves a **plan** (including exiting plan mode) or asks to **implement the plan** / **finish the todos**:

1. Deliver **only the next gate artifact** (usually Phase 0 wireframe).
2. **End the turn.** Tell the user how to open the wireframe (path + `xdg-open` or equivalent).
3. **Wait** for explicit design approval in chat (e.g. “wireframe approved”, “design LGTM”) before **any** `specs/` work.
4. Repeat for spec, architecture, then tests/implementation — **one gate per approval**, unless the user explicitly approves multiple gates in one message.

Batching Phase 0→4 in a single agent run after plan approval is a **protocol violation**, even if todos list all phases.

| Phase | Deliverable | Gate |
|-------|-------------|------|
| **0 — Design (wireframe)** | Create or update `wireframes/<screen>.html` (self-contained HTML/CSS) | **Stop.** Ask for UX/design approval. Do not write or change `specs/` until approved. |
| **1 — Spec** | Create or update `specs/<feature>/SPEC.md` (BDD, out of scope, aligned with approved wireframe) | **Stop.** Ask for spec approval. Do not touch production source until approved. |
| **2 — Architecture** | Domain types and ports in `src/spacemaker/domain/` and `src/spacemaker/ports/` | **Stop.** Ask for approval before tests and adapters. |
| **3 — Tests** | Unit tests from BDD (`tests/unit/`); implementations may be stubs | Run tests; fix test code as needed. |
| **4 — Implementation** | Application use cases, adapters, FastAPI/Web UI, desktop | Until tests pass. Production UI must match approved wireframe unless spec is updated and re-approved. |

### What counts as “production source” (Phases 2–4)

Requires prior **design + spec** approvals (and architecture approval before Phase 3–4):

- `src/spacemaker/` (domain, ports, application, adapters, bootstrap)
- `src/spacemaker/adapters/inbound/web/static/` (production HTML/JS/CSS)

Allowed **before** spec approval: `wireframes/`, `specs/`, and edits to `docs/` / `memory/` that support the gate (e.g. playbook notes). Do not “pre-implement” in `src/` while waiting for approval.

### After approval

When the user explicitly approves the wireframe, proceed to Phase 1 only. When they explicitly approve the spec, proceed to Phase 2. If Phase 4 reveals a spec flaw, **rewrite the spec** (Phase 1), get **re-approval**, then update ports and tests. Do not patch around a bad spec.

**Production UI** under `static/` must match an **approved** wireframe. If code landed before wireframe approval, treat it as provisional — do not call the UI “done” until design is approved and production is reconciled to the wireframe.

Skill: `.cursor/skills/sdd-feature/SKILL.md` for the same workflow.

## Code style

- Use **tabs** for indentation in Python and all project source files — not spaces.

## Wireframes

- Location: [wireframes/](wireframes/) — one self-contained HTML file per screen or flow (embedded CSS; vanilla JS only for wireframe navigation mocks).
- **Before** writing or changing `specs/<feature>/SPEC.md` for a new screen, create or update the wireframe and get UX approval.
- Production UI lives under `src/spacemaker/adapters/inbound/web/static/` and must match approved wireframes unless the spec is updated explicitly.

## Architecture rules

- **`src/spacemaker/domain/`:** entities, value objects, errors. Stdlib only.
- **`src/spacemaker/ports/`:** outbound ports (`DeviceRepository`, `MediaConverter`, `FileSystem`, etc.). Domain + `typing.Protocol` only. Use cases live in `application/`, not separate inbound port modules.
- **`src/spacemaker/application/`:** use cases (`ExtractMedia`, `ConvertMedia`, `GenerateGallery`). No FastAPI, FFmpeg, adb, or filesystem I/O.
- **`src/spacemaker/adapters/`:** inbound (FastAPI, static web UI) and outbound (FFmpeg, adb/MTP, filesystem).
- **`src/spacemaker/bootstrap/`:** composition root; **`desktop.py`:** pywebview entry.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/playbooks/SpaceMaker-adaptations.md](docs/playbooks/SpaceMaker-adaptations.md).

## Library folders (runtime)

Under the user-chosen library root:

| Folder | Role |
|--------|------|
| `originals/` | Extract destination; convert reads and empties this |
| `converted/` | Gallery source; web-compatible outputs and moved-as-is files |
| `error/` | Encode failed after retry; user can review or move to `converted/` |
| `invalid/` | Unsupported or broken inputs |

Conversion rules: [docs/playbooks/SpaceMaker-adaptations.md](docs/playbooks/SpaceMaker-adaptations.md) and reference script [docs/reference/convert_all_1_1.sh](docs/reference/convert_all_1_1.sh).

Release builds are **portable executables** (Linux **AppImage** primary; optional PyInstaller onefile on other platforms) that **download** pinned third-party CLIs (adb, libmtp, ffmpeg, ffprobe, magick, exiftool) into the user data folder per OS/CPU — [specs/packaging/SPEC.md](specs/packaging/SPEC.md). Legal: [docs/legal/](docs/legal/), [specs/legal/SPEC.md](specs/legal/SPEC.md). Resolution order: managed dir → download → `PATH` (only after setup **Continue** or `SPACEMAKER_DEV=1`). Override dir: `SPACEMAKER_TOOLS_DIR`.

## Reference playbooks

| Doc | Purpose |
|-----|---------|
| `docs/playbooks/hexagonal-architecture.md` | Ports, adapters, composition root |
| `docs/playbooks/spec-driven-development.md` | SDD philosophy and phase gates |
| `docs/playbooks/fast-tests.md` | pytest layout, speed, naming |
| `docs/playbooks/SpaceMaker-adaptations.md` | This repo's overrides (folders, conversion, UI) |

## Codebase knowledge tools (orient before editing)

Two tools exist so you do not need to read large swaths of the codebase up
front. Use them before making non-trivial changes — but they don't skip any
Phase Gate: wireframe → spec → architecture → tests → implementation
approvals are still required for features and architectural changes.

**Semantic knowledge base (MkDocs)** — architecture rationale, domain
concepts, and per-area notes live as plain Markdown under `docs/`. **As an
agent, read those `.md` files directly** (`docs/index.md`,
`docs/ARCHITECTURE.md`, `docs/testing.md`, `docs/playbooks/`) — don't run
`mkdocs serve` and browse rendered HTML just to read them; that's slower and
adds nothing a direct file read doesn't already give you. `mkdocs serve` /
`uv run task docs-serve` is for **humans** browsing the same content as a
searchable site; `uv run task docs-build` is worth running after editing
`docs/` since it also surfaces broken internal links.

**Structural knowledge graph (Graphify)** — the codebase is also indexed as
a queryable knowledge graph by [Graphify](https://github.com/Graphify-Labs/graphify)
(`graphify-out/graph.json` + `graphify-out/GRAPH_REPORT.md`, regenerated and
staged by `.githooks/pre-commit`; see "Developer setup" in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

To map dependencies before editing code, do **not** read the raw
`graph.json` file. Instead, use Graphify's CLI (taskipy wrappers pass
extra args through):

```bash
uv run task graph-explain "<symbol>"          # or: uv run graphify explain "<symbol>"
uv run task graph-path "<source>" "<target>"  # or: uv run graphify path "<source>" "<target>"
uv run task graph-query "<question>"          # or: uv run graphify query "<question>"
uv run task graph-update                      # regenerate by hand, without committing
```

This shows the blast radius of a change without reading every related file
or spending tokens parsing the raw graph JSON. The graph is a generated
artifact, not a substitute for the tests and specs that define correct
behavior.

**Graph fidelity check — `graphify diagnose multigraph`:** not a per-task
step. Run it only after a big refactor (renames/moves that could confuse the
extractor) or when a `graph-explain`/`graph-path`/`graph-query` result looks
suspicious (missing edges, an unexpected empty answer). It reports edge
collapse/dangling-endpoint risk against `graphify-out/graph.json`; a clean
run is 0 collapsed edges and 0 dangling endpoints.

**Query feedback loop — `save-result` / `reflect`:** after a
`graph-explain`/`graph-path`/`graph-query` call that actually informed a
real decision (not trivial one-off lookups), tag the outcome:

```bash
uv run graphify save-result --question "<question>" --answer "<short answer>" \
  --type query --nodes "<Symbol1>" "<Symbol2>" --outcome useful|dead_end|corrected
uv run graphify reflect   # regenerates graphify-out/reflections/LESSONS.md
```

This is deterministic bookkeeping, no LLM — `reflect` just aggregates tagged
outcomes into a per-symbol/per-community "how reliable was this" summary.
`graphify-out/memory/*.md` and `graphify-out/reflections/LESSONS.md` are
git-tracked (see `.gitignore`) so the signal accumulates across sessions and
branches instead of resetting per clone.

`LESSONS.md` is **not** a replacement for `memory/decisions.md`: `LESSONS.md`
is auto-generated, per-symbol "was this graph node useful when queried"
signal; `decisions.md` is hand-written, per-decision "why we built it this
way" narrative. They serve different questions and both stay.

**Not enabled yet, possible future option:** `graphify extract` also
supports indexing `docs/` (and PDFs) into the *same* graph via an LLM
backend (`--code-only` is what currently opts us out of that). This would
let `explain`/`path`/`query` connect prose concepts to code symbols
directly. Not worth it yet at this doc corpus's size, and it costs an LLM
API key + tokens + non-determinism — revisit if `docs/` grows enough that
plain file reads stop being sufficient.

Also mirrored as an always-on rule for both agents (pointer only — this
section is the source of truth): `.cursor/rules/graphrag-tools.mdc` (Cursor)
and `.claude/rules/graphrag-tools.md` (Claude Code).

## Rules — Cursor vs Claude Code

Both tools read this file (`AGENTS.md`) as project instructions, plus a set
of always-on rules with the same content, kept in two parallel directories:

- `.cursor/rules/*.mdc` — Cursor's format: YAML frontmatter with
  `description`/`globs`/`alwaysApply`.
- `.claude/rules/*.md` — Claude Code's format (see
  [Claude Code's rules docs](https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/)):
  plain markdown, no frontmatter needed for an always-on rule (Claude Code
  only reads a `paths` field for path-scoped rules; every other frontmatter
  key is silently ignored). Confirmed loading via `/context` → **Memory
  files**.

**These are hand-maintained duplicates, not symlinks.** A symlink was tried
first and rejected: Claude Code only discovers files with a literal `.md`
extension, so a symlink pointing at a `.mdc` file (even one renamed to end in
`.md`) was not picked up in this environment — plain copies in the native
format were required instead. When editing one of the five rules below,
update both the `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md`
copies; a mismatch between them is a bug, not an intentional fork.

## Skills

Project workflows:

- `.cursor/skills/sdd-feature/` — SDD workflow for new/changed flows
- `.cursor/skills/hexagonal-python/` — file placement and port naming
- `.cursor/skills/playbooks/` — when to read full playbooks vs adaptations
- `.cursor/skills/agent-memory/` — memory bank updates and hand-off
- `.cursor/skills/fast-tests/` — pytest conventions (srxy-style)
- `.cursor/skills/save-changes/` — memory update, commit, push (`/save-changes`)
- `.cursor/skills/apply-worktree/` — merge agent worktree into main checkout + `uv run task checks`
- `.cursor/skills/delete-worktree/` — remove isolated worktree after apply

Always-on rules (see "Rules — Cursor vs Claude Code" above): `agent-memory`,
`sdd`, `hexagonal-python`, `playbooks`, `graphrag-tools` — each present as
both `.cursor/rules/<name>.mdc` and `.claude/rules/<name>.md`.

## Quality gate

Requires [uv](https://docs.astral.sh/uv/). Python: **ruff**, **ty**, **pytest** via `uv run task checks` ([scripts/quality/checks.sh](scripts/quality/checks.sh)). Web JS/HTML: **Biome** via `npm ci && npm run check`. See [docs/playbooks/fast-tests.md](docs/playbooks/fast-tests.md).

## Source of truth

`specs/` holds feature specifications. `wireframes/` holds UX layout truth before specs. `memory/` holds per-branch agent state. External trackers track work; the repo tracks truth.
