---
name: hexagonal-python
description: File placement and port naming for SpaceMaker hexagonal layout. Use when adding use cases, ports, adapters, or refactoring layers.
---

# Hexagonal Python (SpaceMaker)

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

## Import guard

Domain and application must not import `fastapi`, `uvicorn`, or adapter modules. Verify with ripgrep when unsure.

## Conversion

Policy in application layer; subprocess command lines in `adapters/outbound/` aligned with `docs/reference/convert_all_1_1.sh`.
