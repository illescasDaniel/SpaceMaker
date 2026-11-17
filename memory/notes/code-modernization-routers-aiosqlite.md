---
name: code-modernization-routers-aiosqlite
description: APIRouter modules, AppServices mixins, TS-authored shell UI, aiosqlite gallery index; HTTP/3 rejected
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

Code modernization: split hubs, aiosqlite, no HTTP/3.

- **Context:** Production hubs exceeded 600 lines (`app.js`, `index.html` CSS, `services.py`, `app.py`). User asked for file separation, async HTTP honesty, strict typing, TypeScript, and HTTP/3 QUIC — then dropped HTTP/3 because TLS/certs are a poor fit for loopback desktop + LAN QR phones.
- **Decision:** (1) FastAPI `APIRouter` modules under `adapters/inbound/web/routes/`; `AppServices` mixins package under `bootstrap/services/`; shell CSS extracted to `static/shell-*.css`; shell UI authored in `web/src/*.ts` and emitted to `static/js/` (`main.js` ES module entry). (2) Gallery index uses **aiosqlite** with async `GalleryIndexPort` / use cases / gallery routes; sync workers bridge via `AppServices.run_coro` (helper-thread `asyncio.run` when already on the ASGI loop). Per-operation DB connections avoid cross-loop cache bugs. (3) **No HTTP/3 / TLS** — stay on uvicorn plain HTTP. (4) Strict TypeScript (`web/tsconfig.json`: `strict`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`; core modules fully typed, feature modules migrate behind `@ts-nocheck`). (5) Production Python: ruff ANN on `src/spacemaker/`, ty-clean mixins via `self: AppServices`, TypedDict gallery serializers.
- **Rationale:** Keeps hexagonal boundaries while making files reviewable; async SQLite matches FastAPI without rewriting subprocess adapters; HTTP/3 would force cert UX on phones and pywebview for little localhost gain.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — Code modernization: split hubs, aiosqlite, no HTTP/3".
