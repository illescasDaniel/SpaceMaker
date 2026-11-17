---
name: compression-reference-script
description: docs/reference/convert_all_1_1.sh is the authoritative compression reference
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

Compression reference.

- **Context:** User's bash script encodes AVIF/AV1 rules, DNG+JPEG collision names, web-compat skip, size rollback.
- **Decision:** Vend `docs/reference/convert_all_1_1.sh` as authoritative compression reference; domain policy documented in `docs/playbooks/SpaceMaker-adaptations.md` and future specs.
- **Rationale:** Single repo-truth for FFmpeg/ImageMagick flags during spec and adapter implementation.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — Compression reference".
