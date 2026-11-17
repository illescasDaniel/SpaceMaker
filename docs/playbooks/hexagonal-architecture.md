---
id: DOC-008
title: "Hexagonal architecture playbook"
summary: "Ports-and-adapters principles, how they map to Python packages in SpaceMaker, golden rules and dependency injection"
type: explanation
status: current
updated: 2026-09-29
verified:
covers: [src/spacemaker/**]
related: [DOC-002]
supersedes:
superseded_by:
---

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
| Ports | `src/spacemaker/ports/outbound/` (use cases in `application/`) |
| Use cases | `src/spacemaker/application/` |
| Inbound adapters | `src/spacemaker/adapters/inbound/web/` |
| Outbound adapters | `src/spacemaker/adapters/outbound/` |
| Composition root | `src/spacemaker/bootstrap/` |

## Golden rules

- Protocols in `ports/`; implementations only in `adapters/`.
- Domain never imports FastAPI or subprocess.
- Conversion **decisions** (where a file goes) in application/domain; **tool invocation** in outbound adapters.
- Trust boundary (from the spec's Design decisions): validate untrusted input (paths, filenames, LAN requests) in inbound adapters/application, not in domain.
- WebSocket progress events are inbound adapter concerns driven by use case callbacks.

## DI

`bootstrap.services.create_app()` constructs outbound adapters, injects into use cases, registers FastAPI routes.
