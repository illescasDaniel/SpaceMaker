# Hexagonal architecture (SpaceMaker)

## Principles

- Dependencies point inward.
- **Inbound ports:** use cases the UI/API invokes.
- **Outbound ports:** device access, media conversion, filesystem.
- **Adapters** implement ports and translate to FFmpeg, adb, HTTP, etc.

## Python mapping

| Concept | Path |
|---------|------|
| Domain | `src/spacemaker/domain/` |
| Ports | `src/spacemaker/ports/inbound/`, `outbound/` |
| Use cases | `src/spacemaker/application/` |
| Inbound adapters | `src/spacemaker/adapters/inbound/web/` |
| Outbound adapters | `src/spacemaker/adapters/outbound/` |
| Composition root | `src/spacemaker/bootstrap.py` |

## Golden rules

- Protocols in `ports/`; implementations only in `adapters/`.
- Domain never imports FastAPI or subprocess.
- Conversion **decisions** (where a file goes) in application/domain; **tool invocation** in outbound adapters.
- WebSocket progress events are inbound adapter concerns driven by use case callbacks.

## DI

`bootstrap.build_services()` constructs outbound adapters, injects into use cases, registers FastAPI dependencies.
