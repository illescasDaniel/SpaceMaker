---
name: compress-media-preference
description: Compress media preference on disk (preferences.json) with its own ports; full SDD
type: decision
date: 2026-09-26
status: current
supersedes:
superseded_by:
source:
---

Photo backup Compress media: disk preferences + Easy UI (full SDD).

- **Context:** Approved wireframe + easy-mode spec + architecture for a **Compress media** checkbox on Photo backup (Easy): default on, forced off when compression CLIs missing, persisted across launches, gates Easy auto-convert.
- **Decision:** (1) Domain `compress_media.py` + ports `UserPreferencesPort` / `CompressionToolsPort`. (2) Adapter `JsonUserPreferences` at `{spacemaker_data_dir}/preferences.json` (atomic write); `ManagedCompressionTools` over managed-tool snapshot (`magick` + `ffmpeg`). (3) `PUT /api/settings` accepts `compress_media` even during extract; turning on resumes Easy drain. Client omits the field when the checkbox is disabled so a stored “on” is not overwritten while tools are missing. (4) Easy UI matches wireframe (checkbox, ⓘ why/how, tools hint, hide Convert progress when off). Hardware encoders are **not** part of the tools gate.
- **Rationale:** First disk-backed user preference separate from session-only `AppSession`; JSON next to managed-tools data reuses existing OS data-dir layout. Verified live: tools-unavailable forced-off + info panel; unit/integration tests green (unrelated pre-existing raw/magick unit failure when ImageMagick absent).

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-26 — Photo backup Compress media: disk preferences + Easy UI (full SDD)".
