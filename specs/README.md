# Feature specifications

Source of truth for behavior. Wireframes: [wireframes/app.html](../wireframes/app.html).

| Spec | Scope |
|------|--------|
| [home-modules/SPEC.md](home-modules/SPEC.md) | Home hub tiles, module routing, Photo/USB/receive/send entry |
| [easy-mode/SPEC.md](easy-mode/SPEC.md) | Photo backup UI, auto Wi‑Fi receive, convert-as-received, gallery QR |
| [receive-files/SPEC.md](receive-files/SPEC.md) | Phone → PC uploads to Documents/SpaceMaker |
| [send-files/SPEC.md](send-files/SPEC.md) | PC → phone share via QR `/share` |
| [main-wizard/SPEC.md](main-wizard/SPEC.md) | USB three-step wizard, progress, error/invalid warnings |
| [extract-media/SPEC.md](extract-media/SPEC.md) | Device detection, source folders, pause/stop, copy/move, idempotent transfer |
| [convert-media/SPEC.md](convert-media/SPEC.md) | Folder routing, encode policy, retries, user recovery actions |
| [gallery/SPEC.md](gallery/SPEC.md) | Timeline/calendar, `converted/` only, LAN + QR |
| [packaging/SPEC.md](packaging/SPEC.md) | AppImage (Linux), managed CLI downloads per OS/arch |
| [legal/SPEC.md](legal/SPEC.md) | Privacy, disclaimer, third-party notice in release + UI |
| [ui-motion/SPEC.md](ui-motion/SPEC.md) | Shared motion vocabulary, screen/hover/press/list transitions, reduced-motion |

**Phase gate:** Spec approval required before domain/ports (Phase 2).

**Test mapping:** Each BDD scenario → one or more `tests/unit/` functions named `test_given_…_when_…_then_…`. Integration tests cover outbound adapters with mocked subprocesses unless marked `@pytest.mark.integration`.
