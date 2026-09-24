---
paths: ["src/spacemaker/**"]
---
# Hexagonal Architecture (Python)

## Placement

| What | Where |
|------|--------|
| Entities, enums, errors | `src/spacemaker/domain/` |
| Outbound ports | `src/spacemaker/ports/outbound/` |
| Use case impl | `src/spacemaker/application/` |
| FastAPI, static UI, WS | `src/spacemaker/adapters/inbound/web/` |
| FFmpeg, adb, FS | `src/spacemaker/adapters/outbound/` |
| Wiring | `src/spacemaker/bootstrap/` |
| pywebview entry | `src/spacemaker/desktop.py` |

## Naming

- Outbound: `DeviceRepository`, `MediaConverter`, `FileSystem` (Protocol suffix optional)
- Inbound: use case classes in `application/` (no separate `ports/inbound/` tree today)

## Inside core (`domain`, `ports`, `application`)

- Domain entities, value objects, errors
- Outbound ports (`DeviceRepository`, `MediaConverter`, `FileSystem`, …)
- Use case implementations in `application/` (pure orchestration; inject ports)

**Must NOT import:** FastAPI, uvicorn, pywebview, subprocess wrappers tied to ffmpeg/adb, or concrete adapter modules.

**May import:** stdlib; `typing`; other `spacemaker.domain` / `spacemaker.ports` / `spacemaker.application` as appropriate.

Verify with ripgrep when unsure.

## Adapters (`src/spacemaker/adapters/`)

- **Inbound:** FastAPI routes, WebSocket handlers, static web assets
- **Outbound:** FFmpeg/ImageMagick/exiftool executors, adb/MTP, filesystem moves

## Rules

- Use cases depend on outbound ports, never on subprocess or path logic directly
- HTTP/WebSocket handlers depend on inbound ports or use cases, not FFmpeg/adb
- Composition root in `src/spacemaker/bootstrap/` wires adapters → use cases → handlers
- Conversion policy lives in domain/application; FFmpeg flag details live in outbound adapter + `docs/reference/convert_all_1_1.sh`
