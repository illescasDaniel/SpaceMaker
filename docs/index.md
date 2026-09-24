# SpaceMaker — Agent Knowledge Base

This site is the semantic knowledge base for AI agents and contributors working on
SpaceMaker. It complements the structural knowledge graph produced by
[Graphify](https://github.com/Graphify-Labs/graphify) (`graph.json` /
`GRAPH_REPORT.md`) — the graph describes *what calls what*; these pages
describe *why*.

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

### Database Schema

Persistent state and on-disk formats (if/when introduced). Currently SpaceMaker is
filesystem-based — document the `originals/` / `converted/` / `error/` / `invalid/`
library layout here as it evolves.

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
