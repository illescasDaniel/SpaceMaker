---
name: bundle-adb-per-os
description: release builds bundle adb per OS/arch
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: managed-cli-downloads
source:
---

Bundle adb per OS/arch.

- **Context:** User wants ADB included in the final installer/binary, not a separate user install.
- **Decision:** Release builds ship Google platform-tools `adb` (and later libmtp) for each target OS/CPU; `AdbDeviceRepository` resolves bundled path first. PATH fallback only for dev/source runs. Spec: `specs/packaging/SPEC.md`.
- **Rationale:** Matches self-contained desktop app goal; adbutils still drives the client but must point at our binary.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Bundle adb per OS/arch".

Superseded by [managed-cli-downloads](managed-cli-downloads.md).
