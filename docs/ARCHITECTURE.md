# Architecture

SpaceMaker is organized as a **hexagonal (ports & adapters)** Python package:

```
src/spacemaker/
├── domain/              # Pure models, enums, errors (stdlib only)
├── ports/outbound/      # DeviceRepository, MediaConverter, FileSystem, …
├── application/         # Use case orchestration (ExtractMedia, ConvertMedia, …)
├── adapters/
│   ├── inbound/web/     # FastAPI routes, WebSockets, static UI
│   └── outbound/        # FFmpeg, adb/MTP, filesystem
├── bootstrap/           # Composition root (services, paths, managed tools)
└── desktop.py           # pywebview entry (starts local server, opens window)
```

| Layer | Rule |
|-------|------|
| domain | stdlib only |
| ports | domain + `Protocol` |
| application | domain, ports — not FastAPI, subprocess, or UI |
| adapters | concrete I/O, HTTP, desktop shell |

Composition root: `bootstrap.services.create_app()` wires outbound adapters into use cases and FastAPI handlers.

## Runtime flow

1. **Home hub** — four modules: Photo backup (Wi‑Fi library receive), USB photo backup (wizard), Receive files (Documents), Send files (PC → phone). See [specs/home-modules/SPEC.md](../specs/home-modules/SPEC.md).
2. **Extract** — Wi‑Fi QR upload and/or `DeviceRepository` (MTP via **libmtp**, ADB via **adbutils** + `adb`) into `originals/`. Managed tool dir → download → `PATH` after setup. See [specs/packaging/SPEC.md](../specs/packaging/SPEC.md).
3. **Convert** — reads `originals/`, writes `converted/`, or routes failures to `error/` / `invalid/`.
4. **Gallery** — indexes `converted/`; optional LAN URL + QR for phone browsing. Tokenized LAN pages for upload, receive, and share sessions.

Progress for extract and convert streams over WebSockets to the desktop web UI (loopback only). Phone clients use HTTP APIs and tokenized upload/share/receive endpoints.

## Entry-point call chain

`__main__.py` → `spacemaker.desktop.main()`, which parses CLI args (`--port`,
`--host`, `--server-only`, `--gui`), starts the FastAPI/uvicorn server on a
background daemon thread (`desktop.run_server` → `bootstrap.services.create_app`
→ `adapters.inbound.web.app.create_fastapi_app`), and — unless `--server-only`
— opens a **pywebview** desktop window pointed at that local server (falling
back to the system browser if pywebview/Qt WebEngine is unavailable). So
SpaceMaker is a **local web server + native window shell**, not a
client-server product with a remote backend.

## Routing pattern

`create_fastapi_app(services)` builds a **single `FastAPI()` instance** and
registers every route as an inline closure via
`@app.get/post/put/delete/websocket(...)` inside that one function — there is
no separate `APIRouter`/controller-class layer. Routes are grouped by prefix
convention (`/api/gallery/...`, `/api/extract/...`, `/api/convert/...`,
`/api/tools/...`, `/api/receive/...`, `/api/share/...`) rather than by file.
Each handler is a thin adapter that calls into `AppServices` /
application-layer use cases and serializes domain objects to dicts — a
closure-based composition style, not classic MVC. Static SPA shells are
served from `adapters/inbound/web/static/` via a `StaticFiles` mount plus
explicit HTML entry routes (`/`, `/gallery`, `/upload`, `/receive`, `/share`).
A single `/ws` WebSocket endpoint pushes state updates to connected clients.
Request bodies are typed with Pydantic `BaseModel`s.

## Persistence: no database

There is no database. State is:

- **Filesystem-based**, through the `FileSystem` port (`LocalFileSystem`
  adapter) — the library root's `originals/` / `converted/` / `error/` /
  `invalid/` folders are the persistence layer for media.
- **In-process/in-memory** for session/runtime state (`AppSession`, held on
  `AppServices.session`), plus a small metadata cache that is explicitly
  invalidated on writes.
- Long-running work (extract/convert) runs on a `ThreadPoolExecutor` owned by
  `AppServices`, tracked via `Future` handles rather than a job table.

## Refactor-relevant rules

- New outbound capabilities belong behind a **port** in `ports/`, wired to a
  concrete adapter **only** inside `AppServices.__init__` — route handlers
  and use cases must not import adapters directly.
- New use cases go in `application/`, must stay free of FastAPI/FFmpeg/adb
  imports, and are exposed to the web layer through `AppServices` methods,
  not instantiated inline in `app.py`.
- New HTTP routes are added as closures inside `create_fastapi_app`,
  following the existing `/api/<area>/<action>` prefix convention, and
  should reuse `require_loopback` / `require_loopback_websocket` guards for
  anything not meant to be LAN-exposed.

## Developer setup

After cloning, point Git at the repo's version-controlled hooks so the
Graphify knowledge graph (`graph.json` / `GRAPH_REPORT.md`) regenerates and
gets staged automatically on commit (works identically on Windows and
Linux — see `.githooks/pre-commit`):

```bash
git config core.hooksPath .githooks
```

This is a per-clone local setting (not stored in `.git/config` by default
until you run it), so every clone/worktree needs to run it once.

**Expected:** `git status` will usually show `graphify-out/graph.json` /
`GRAPH_REPORT.md` as modified again right after a commit. This is harmless
and permanent, not a bug — the embedded `built_at_commit` field can only
ever reference the *parent* commit (a file can't contain the hash of the
commit that contains it), and it gets re-touched a few seconds after the
hook stages it. Don't try to "fix" it by re-committing.
