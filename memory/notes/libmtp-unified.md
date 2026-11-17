---
name: libmtp-unified
description: libmtp as the single MTP client on all OSs
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: remove-mtp-adb-afc
source:
---

Unified libmtp for MTP adapter.

- **Context:** User asked whether Win/Linux users must install libmtp; OS already exposes MTP in Explorer/file managers.
- **Decision:** libmtp is the **application** MTP client on Windows, Linux, and macOS (one adapter path). User-facing copy: set phone to MTP only; do not tell Win/Linux users to install libmtp. Packaged app bundles libmtp tools when feasible.
- **Rationale:** Native OS MTP is for humans; SpaceMaker still needs libmtp (or equivalent) in code. Single stack beats WPD/gphoto2 split for v1.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Unified libmtp for MTP adapter".

Superseded by [remove-mtp-adb-afc](remove-mtp-adb-afc.md).
