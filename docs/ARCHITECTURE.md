# Architecture

SpaceMaker is organized as a **hexagonal (ports & adapters)** Python package:

```
src/spacemaker/
├── domain/              # Pure models, enums, errors (stdlib only)
├── ports/
│   ├── inbound/         # Use-case ports (ExtractMedia, ConvertMedia, …)
│   └── outbound/        # DeviceRepository, MediaConverter, FileSystem, …
├── application/         # Use case orchestration
├── adapters/
│   ├── inbound/web/     # FastAPI routes, WebSockets, static UI
│   └── outbound/        # FFmpeg, adb/MTP, filesystem
├── bootstrap.py         # DI factories
└── desktop.py           # pywebview entry (starts local server, opens window)
```

| Layer | Rule |
|-------|------|
| domain | stdlib only |
| ports | domain + `Protocol` |
| application | domain, ports — not FastAPI, subprocess, or UI |
| adapters | concrete I/O, HTTP, desktop shell |

Composition root: `bootstrap.build_services()` wires outbound adapters into use cases and inbound handlers.

## Runtime flow

1. **Extract** — `DeviceRepository` (MTP via bundled **libmtp**, or ADB via **adbutils** + bundled platform-tools `adb`) copies or moves media into `originals/` (idempotent transfer). See [specs/packaging/SPEC.md](../specs/packaging/SPEC.md).
2. **Convert** — reads `originals/`, writes `converted/`, or moves failures to `error/` / `invalid/` per policy.
3. **Gallery** — serves and indexes `converted/` only; optional LAN URL + QR for phone access.

Progress for extract and convert streams over WebSockets to the web UI inside pywebview.
