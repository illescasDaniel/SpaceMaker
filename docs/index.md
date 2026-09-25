# SpaceMaker — Agent Knowledge Base

This site is the semantic knowledge base for AI agents and contributors working on
SpaceMaker. It complements the `codenav` MCP server (see
[agent-tooling.md](agent-tooling.md)), which answers *what calls what*
through `ty`'s type-resolved code navigation; these pages describe *why*.

Serve locally with:

```bash
uv run mkdocs serve
```

## Sections

Fill each section below as the corresponding area of the codebase stabilizes.
Do not paste raw source files here — summarize intent, decisions, and gotchas.

### Architecture

High-level system design, hexagonal layering (domain / ports / application / adapters),
and the composition root. See `docs/ARCHITECTURE.md` for the current authoritative doc;
migrate or link it here as this site matures.

### API Routes

Inbound HTTP/FastAPI surface: endpoints, request/response shapes, and the use cases
they invoke.

### Persistence

There is no database — SpaceMaker is filesystem-based. See
`docs/ARCHITECTURE.md` "Persistence: no database" for the
`originals/` / `converted/` / `error/` / `invalid/` library layout and how
runtime state is held. If a database is ever introduced, give it its own
`docs/database.md` page (schema rules, migration protocol) and add it to
`mkdocs.yml` nav at that point.

### Testing

BDD given/when/then conventions, mocking standards, and the quality gate —
see `docs/testing.md`.

### AI Prompts

Any prompts or agent-facing instructions embedded in the product itself (as opposed to
development tooling instructions, which live in `AGENTS.md`).

### Domain Model

Core entities, value objects, and invariants living in `src/spacemaker/domain/`.

### Ports & Adapters

Outbound ports (`src/spacemaker/ports/`) and their concrete adapters
(`src/spacemaker/adapters/`) — FFmpeg, adb/MTP, filesystem, web UI.

### Specs & Wireframes

Pointers into `specs/` and `wireframes/`, which remain the source of truth for
feature behavior and UX until mirrored here.
