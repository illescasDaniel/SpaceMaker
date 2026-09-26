_Last updated: 2026-09-26_

## Branch

`cursor/gallery-orphan-cache-cleanup-2e72`

## Current focus

Gallery orphan cache cleanup — **implemented** (spec + architecture approved;
Phases 3–4 done). Ready for review / merge. Branch updated with `main`
(includes merged DNG convert unit-test stub fix, PR #5).

## Just changed

- Domain: `gallery_cache_paths.py` (injective thumb/export paths); removed
  legacy `export_cache_filename`
- Application: `gallery_cache_cleanup.py`; `DeleteGalleryItem`,
  `SyncGalleryIndex`, `ExportFriendlyMedia` wired for GC + path-mirrored
  exports
- Adapter: `SubprocessThumbnailGenerator` uses `thumbnail_path`
- Tests: cache paths, delete, sync orphan/changed/legacy sweep, export reuse

## Next steps

- PR review / merge of #4
- No further code planned on this thread unless review feedback

## Run

```bash
uv run task checks
uv run pytest tests/unit/test_gallery_cache_paths.py tests/unit/test_delete_gallery_item.py tests/unit/test_sync_gallery_index.py tests/unit/test_gallery_export.py tests/unit/test_raw_image_convert.py
```
