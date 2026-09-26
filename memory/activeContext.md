_Last updated: 2026-09-26_

## Branch

`cursor/photo-backup-convert-toggle-50ae`

## Current focus

**Phase 2 (architecture)** — Photo backup **Compress media** preference.

Wireframe + spec approved 2026-09-26. Domain + ports added; no adapters/UI yet.

## Blockers

Waiting for **explicit architecture approval** in chat before Phase 3 (tests) / Phase 4 (adapters + UI).

## Next steps

1. User reviews architecture → reply **architecture approved** (or change requests).
2. Phase 3: unit tests for `resolve_compress_media_preference`, tools gate, auto-drain when compress off.
3. Phase 4: JSON/preferences adapter, CompressionTools adapter, settings API + Easy UI.

## Just changed

- `src/spacemaker/domain/compress_media.py` — preference resolution
- `src/spacemaker/domain/convert_policy.py` — `compress_media` gate on auto-drain
- `src/spacemaker/ports/outbound/user_preferences.py`
- `src/spacemaker/ports/outbound/compression_tools.py`
- `docs/ARCHITECTURE.md`, `memory/decisions.md`
