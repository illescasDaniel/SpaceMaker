# Feature specifications

Source of truth for behavior. Wireframes: [wireframes/app.html](../wireframes/app.html).

| Spec | Scope |
|------|--------|
| [easy-mode/SPEC.md](easy-mode/SPEC.md) | Default Easy UI, auto Wi‑Fi receive, convert-as-received, gallery QR |
| [main-wizard/SPEC.md](main-wizard/SPEC.md) | Advanced 3-step UI, progress, error/invalid warnings, desktop shell |
| [extract-media/SPEC.md](extract-media/SPEC.md) | Device detection, source folders, pause/stop, copy/move, idempotent transfer |
| [convert-media/SPEC.md](convert-media/SPEC.md) | Folder routing, encode policy, retries, user recovery actions |
| [gallery/SPEC.md](gallery/SPEC.md) | Timeline/calendar, `converted/` only, LAN + QR |
| [packaging/SPEC.md](packaging/SPEC.md) | PyInstaller, all bundled CLIs per OS/arch |
| [legal/SPEC.md](legal/SPEC.md) | Privacy, disclaimer, third-party notice in installer |

**Phase gate:** Spec approval required before domain/ports (Phase 2).

**Test mapping:** Each BDD scenario → one or more `tests/unit/` functions named `test_given_…_when_…_then_…`. Integration tests cover outbound adapters with mocked subprocesses unless marked `@pytest.mark.integration`.
