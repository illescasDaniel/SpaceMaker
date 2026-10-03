# Architecture

SpaceMaker is organized as a **hexagonal (ports & adapters)** Python package:

```
src/spacemaker/
├── domain/              # Pure models, enums, errors (stdlib only)
├── ports/outbound/      # DeviceRepository, MediaConverter, FileSystem, …
├── application/         # Use case orchestration (ExtractMedia, ConvertMedia, …)
├── adapters/
│   ├── inbound/web/     # FastAPI routes, WebSockets, static UI
│   └── outbound/        # FFmpeg, adb/AFC, filesystem
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

1. **Home hub** — six modules: Photo backup (Wi‑Fi library receive), USB photo backup (wizard), **USB file transfer** (cable → Documents, no convert), Receive files (Documents), Send files (PC → phone), Transfer files (temporary multi-device upload+download). See [specs/home-modules/SPEC.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/home-modules/SPEC.md), [specs/usb-file-transfer/SPEC.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/usb-file-transfer/SPEC.md), [specs/transfer-files/SPEC.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/transfer-files/SPEC.md).
2. **Extract** — Wi‑Fi QR upload and/or `DeviceRepository` (ADB via **adbutils** + `adb`, iPhone AFC via **ifuse**) into `originals/`. Managed tool dir → download → `PATH` after setup. See [specs/packaging/SPEC.md](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/packaging/SPEC.md).
3. **USB file transfer** — `TransferUsbFiles` + `DeviceRepository.list_file_paths` / `list_extra_file_paths` (ADB/AFC); Add files/folder via **adbfs** / **ifuse** mounts into `documents_directory()/SpaceMaker/` with Android storage prefixes stripped; reuses pause/stop control; no convert/gallery.
4. **Convert** — reads `originals/`, writes `processed/`, or routes failures to `error/` / `invalid/`. When Compress media is off (Easy), uploads are promoted as-is into `processed/`.
5. **Gallery** — indexes `processed/`; optional LAN URL + QR for phone browsing. Tokenized LAN pages for upload, receive, share, and transfer sessions.

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

`create_fastapi_app(services)` builds a **single `FastAPI()` instance**, mounts
static files, installs CSP/cache middleware, then registers **`APIRouter`**
modules from `adapters/inbound/web/routes/` via `register_routes` — one builder
per area (`pages`, `settings`, `lan`, `extract`, `usb_transfer`, `convert`,
`gallery`, `media`, `tools`, `websocket`). Shared request models live in
`models.py`; path helpers in `media_paths.py`; serializers in `serializers.py`.

Each `build_*_router(services)` closes over `AppServices` (same thin-adapter
style as before). Routes use `/api/<area>/…` prefixes. Static SPA shells are
served from `adapters/inbound/web/static/` (`index.html` / `gallery_mobile.html`
+ CSS sheets). Shell UI sources live in `web/src/*.ts` (strict TypeScript;
`npm run build:web` / `tsc -p web/tsconfig.json` emits ES modules to
`static/js/`; the shell loads `/static/js/main.js` as `type="module"`).
Modules call each other via direct named imports — there is no runtime
service-locator/registry, and every exported function carries explicit
parameter/return types (no `// @ts-nocheck`/`@ts-ignore`). Relative imports
name the real `./x.ts` source file; `tsconfig.json`'s
`rewriteRelativeImportExtensions` rewrites them to `./x.js` in the emitted
output so the importmap cache-busting scheme is unaffected.
`tests/unit/test_web_typing.py` guards these conventions. A
single `/ws` WebSocket pushes state to loopback desktop clients. Request
bodies use Pydantic `BaseModel`s.

Gallery index reads/writes go through **async** `GalleryIndexPort` /
`SqliteGalleryIndex` (**aiosqlite**). Gallery HTTP handlers are `async def` and
`await` use cases; worker threads bridge with `AppServices.run_coro`.

Composition root: `bootstrap/services/` package (`AppServices` + mixins for
snapshots, LAN sessions, jobs, USB browse). Mixin methods annotate
`self: AppServices` so the type checker sees the composed surface.

**Network passcode:** optional LAN access control ([spec](https://github.com/illescasDaniel/SpaceMaker/blob/main/specs/network-passcode/SPEC.md)). One middleware (`adapters/inbound/web/passcode_guard.py`) challenges every non-loopback request with 401 while a passcode is set; `application/network_passcode.py` owns the scrypt record (`network_passcode.json`, separate from preferences), HMAC-derived login cookie / QR token and per-IP lockout. Not encryption.

**HTTP transport:** plain HTTP on uvicorn (loopback desktop + LAN QR). No
HTTP/3 / QUIC / TLS — certs are a poor fit for this deployment model.

## Persistence: filesystem + derived SQLite index

There is no database of record — the filesystem remains the source of truth.
State is:

- **Filesystem-based**, through the `FileSystem` port (`LocalFileSystem`
  adapter) — the library root's `originals/` / `processed/` / `error/` /
  `invalid/` folders are the persistence layer for media.
- **A derived, fully-rebuildable SQLite index**
  (`{library_root}/.index.sqlite`, via the `GalleryIndexPort` /
  `SqliteGalleryIndex` adapter) that caches gallery metadata (captured date,
  kind, mtime, size) for fast keyset-paginated timeline, calendar, and
  neighbor queries at large library sizes. It is incrementally synced against
  the filesystem by diffing mtime/size (`SyncGalleryIndex`), and is safe to
  delete at any time — it rebuilds itself from `processed/` + EXIF/ffprobe on
  next gallery load.
- **In-process/in-memory** for session/runtime state (`AppSession`, held on
  `AppServices.session`).
- **Disk-backed user preferences** via `UserPreferencesPort` (e.g. Photo backup
  **Compress media** on/off) — survive app relaunch; distinct from session-only
  fields like `ui_mode`. Compression tool readiness is exposed through
  `CompressionToolsPort` (magick + ffmpeg resolvable), with effective checkbox
  state resolved in `domain/compress_media.py`.
- Long-running work (extract/convert) runs on a `ThreadPoolExecutor` owned by
  `AppServices`, tracked via `Future` handles rather than a job table.

## Logging

A rotating file log (`{data_dir}/logs/spacemaker.log`, 3 × 5 MB, next to
`preferences.json`) is configured once at process start
(`bootstrap/logging_setup.py`, called from `desktop.py`'s `main()`) by
attaching a handler to the `"spacemaker"` logger. Every module gets file
logging for free via `logging.getLogger(__name__)`, since all package
loggers live under the `spacemaker.*` name and propagate up to it — no
per-module setup needed. This exists so failures that are otherwise
invisible to the UI (a convert job's per-file failure reason, a thumbnail
generation crash) survive an app restart and can be inspected later,
rather than only living in transient in-memory session state
(`AppSession.last_error`).

## Refactor-relevant rules

- New outbound capabilities belong behind a **port** in `ports/`, wired to a
  concrete adapter **only** inside `AppServices.__init__` — route handlers
  and use cases must not import adapters directly.
- New use cases go in `application/`, must stay free of FastAPI/FFmpeg/adb
  imports, and are exposed to the web layer through `AppServices` methods,
  not instantiated inline in `app.py`.
- New HTTP routes are added as `build_*_router` closures in
  `adapters/inbound/web/routes/`, registered from `register_routes`, following
  the existing `/api/<area>/<action>` prefix convention, and should reuse
  `require_loopback` / `require_loopback_websocket` guards for anything not
  meant to be LAN-exposed.

## Developer setup

See [agent-tooling.md](agent-tooling.md) for the `codenav` and `webnav` MCP
servers, the Cursor/Claude Code rule-pairing scheme, and other
Windows/tooling gotchas.
