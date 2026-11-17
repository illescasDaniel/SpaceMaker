---
name: mtp-default-adb-recommended
description: Step 1 defaulted to MTP with ADB recommended
type: decision
date: 2026-09-22
status: superseded
supersedes:
superseded_by: remove-mtp-adb-afc
source:
---

MTP default, ADB recommended.

- **Context:** User chose default extract path and platform tooling.
- **Decision:** Step 1 defaults to MTP; toggle to ADB (recommended) with info help. adbutils for ADB on all platforms.
- **Rationale:** Lower friction for casual users; ADB labeled recommended for speed/reliability when debugging is enabled.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — MTP default, ADB recommended".

Superseded by [remove-mtp-adb-afc](remove-mtp-adb-afc.md).
