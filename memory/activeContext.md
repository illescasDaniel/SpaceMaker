_Last updated: 2026-09-26_

## Branch

`cursor/usb-file-transfer-c861`

## Current focus

**USB file transfer** — SDD Phase 2 architecture done; awaiting **architecture approval**.

Wireframe + spec approved 2026-09-26.

## Just changed

- Domain: `transfer_folders.py`, `usb_file_transfer.py`, `AppModule.USB_FILE_TRANSFER`
- Port: `DeviceRepositoryPort.list_file_paths` (+ adapter stubs / fake)
- Use case: `application/transfer_usb_files.py`
- Docs: ARCHITECTURE, decisions, SPEC metadata

## Next steps

1. User replies **architecture approved** (or changes).
2. Then Phases 3–4: unit tests from BDD, then adapter `list_file_paths` + web UI/wiring.
