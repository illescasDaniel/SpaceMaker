_Last updated: 2026-09-26_

## Branch

`cursor/gallery-orphan-cache-cleanup-2e72`

## Current focus

Gallery orphan cache cleanup. Spec approved. **Phase 2 domain helpers landed —
waiting on explicit architecture approval** before tests / use-case / adapter
wiring (SDD gate).

## Architecture (Phase 2)

No new ports — `FileSystemPort` already covers exists/delete. Domain:

- [`gallery_cache_paths.py`](src/spacemaker/domain/gallery_cache_paths.py):
  `thumbnail_path`, `export_cache_path`, `export_cache_paths_for_relative`,
  `is_legacy_hash_export_filename`
- [`library_paths.py`](src/spacemaker/domain/library_paths.py):
  `THUMBNAILS_DIR_NAME` / `EXPORTS_DIR_NAME` constants
- Legacy `export_cache_filename` kept until Phase 4 rewires
  `ExportFriendlyMedia` / delete / sync

## Next steps

1. User: reply **architecture approved** (or requested changes).
2. Then: Phases 3–4 — unit tests + ExportFriendlyMedia / thumb generator /
   DeleteGalleryItem / SyncGalleryIndex + remove legacy hash helper.

## Run

```bash
uv run task spacemaker
uv run task checks
```
