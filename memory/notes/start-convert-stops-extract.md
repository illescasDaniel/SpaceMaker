---
name: start-convert-stops-extract
description: starting convert stops an active extract gracefully first
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

Start convert stops active extract.

- **Context:** Users may want to convert files already in `originals/` without manually stopping extract first (common during Wi‑Fi receive).
- **Decision:** `can_start_convert` depends only on `originals/` count. `start_convert` calls `stop_extract_and_wait()` (graceful stop + USB thread join + Wi‑Fi in-flight drain) before starting convert.
- **Rationale:** One-click flow; avoids racing extract writes against convert reads.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Start convert stops active extract".
