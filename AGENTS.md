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

1. **Phase 0 — Wireframe:** Create or update `wireframes/<screen>.html` (self-contained HTML/CSS). Stop and ask for human UX approval before proceeding.
2. **Phase 1 — Spec:** Read or write the relevant `specs/<feature>/SPEC.md`. Stop and ask for human approval before proceeding.
3. **Phase 2 — Architecture:** Write or update domain types and ports in `src/spacemaker/domain/` and `src/spacemaker/ports/`. Stop and ask for approval.
4. **Phase 3 — Tests:** Write unit tests from the BDD acceptance criteria. Tests must run; implementations may be stubs.
5. **Phase 4 — Implementation:** Write adapters, application use cases, FastAPI/Web UI, and desktop wrapper until tests pass.

If Phase 4 reveals a flaw in the spec, **rewrite the spec** (Phase 1), then update ports and tests. Do not patch around a bad spec.

## Code style

- Use **tabs** for indentation in Python and all project source files — not spaces.

## Wireframes

- Location: [wireframes/](wireframes/) — one self-contained HTML file per screen or flow (embedded CSS; vanilla JS only for wireframe navigation mocks).
- **Before** writing or changing `specs/<feature>/SPEC.md` for a new screen, create or update the wireframe and get UX approval.
- Production UI lives under `src/spacemaker/adapters/inbound/web/static/` and must match approved wireframes unless the spec is updated explicitly.

## Architecture rules

- **`src/spacemaker/domain/`:** entities, value objects, errors. Stdlib only.
- **`src/spacemaker/ports/`:** inbound use-case ports and outbound ports (`DeviceRepository`, `MediaConverter`, `FileSystem`, etc.). Domain + `typing.Protocol` only.
- **`src/spacemaker/application/`:** use cases (`ExtractMedia`, `ConvertMedia`, `GenerateGallery`). No FastAPI, FFmpeg, adb, or filesystem I/O.
- **`src/spacemaker/adapters/`:** inbound (FastAPI, static web UI) and outbound (FFmpeg, adb/MTP, filesystem).
- **`bootstrap.py`:** composition root; **`desktop.py`:** pywebview entry.

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

Release builds bundle **all** third-party CLIs (adb, libmtp, ffmpeg, ffprobe, magick, exiftool) per OS/CPU — [specs/packaging/SPEC.md](specs/packaging/SPEC.md). Legal: [docs/legal/](docs/legal/), [specs/legal/SPEC.md](specs/legal/SPEC.md). Dev may use tools on `PATH`; frozen app must not require manual installs.

## Reference playbooks

| Doc | Purpose |
|-----|---------|
| `docs/playbooks/hexagonal-architecture.md` | Ports, adapters, composition root |
| `docs/playbooks/spec-driven-development.md` | SDD philosophy and phase gates |
| `docs/playbooks/fast-tests.md` | pytest layout, speed, naming |
| `docs/playbooks/SpaceMaker-adaptations.md` | This repo's overrides (folders, conversion, UI) |

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

Always-on rules: `agent-memory.mdc`, `sdd.mdc`, `hexagonal-python.mdc`, `playbooks.mdc`.

## Quality gate

Requires [uv](https://docs.astral.sh/uv/). Python: **ruff**, **ty**, **pytest** via `uv run task checks` ([scripts/quality/checks.sh](scripts/quality/checks.sh)). Web JS/HTML: **Biome** via `npm ci && npm run check`. See [docs/playbooks/fast-tests.md](docs/playbooks/fast-tests.md).

## Source of truth

`specs/` holds feature specifications. `wireframes/` holds UX layout truth before specs. `memory/` holds per-branch agent state. External trackers track work; the repo tracks truth.
