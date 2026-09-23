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
