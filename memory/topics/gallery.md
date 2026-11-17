# Gallery
Updated: 2026-11-17. The processed/ gallery: index, thumbnails, item page, batch actions and export.

## Now
The gallery reads a derived, rebuildable SQLite index ([gallery-sqlite-index-50k](../notes/gallery-sqlite-index-50k.md)) through aiosqlite ([code-modernization-routers-aiosqlite](../notes/code-modernization-routers-aiosqlite.md)); thumbnails keep the source aspect ratio ([thumbnails-fit-within](../notes/thumbnails-fit-within.md)) in path-mirrored caches ([gallery-cache-path-mirrored](../notes/gallery-cache-path-mirrored.md)); batch delete goes to the system trash ([gallery-batch-trash-and-cpu-export](../notes/gallery-batch-trash-and-cpu-export.md)).

## How it got here
- 2026-09-25 in-memory cache replaced by the SQLite index for 50k+ items ([note](../notes/gallery-sqlite-index-50k.md)).

## Notes
- [Gallery batch: send2trash, CPU libx264 behind a confirm, zips in `.exports/.batch`](../notes/gallery-batch-trash-and-cpu-export.md) 2026-10-18: send2trash only (no hard delete); gallery MP4 export may use CPU libx264 after a 409 confirm; library convert stays GPU-only
- [Open in Maps: desktop `js_api` bridge with server-side URL re-validation](../notes/gallery-open-in-maps-revalidated-url.md) 2026-10-02: EXIF GPS is untrusted: the desktop bridge re-parses and rebuilds the Maps URL before opening it
- [Gallery delete: remove the tile in place, never reload the timeline](../notes/gallery-delete-in-place.md) 2026-09-29: deleting removes the tile in place and never reloads the timeline; removal starts after the fade-in
- [Code modernization: split hubs, aiosqlite, no HTTP/3](../notes/code-modernization-routers-aiosqlite.md) 2026-09-28: APIRouter modules, AppServices mixins, TS-authored shell UI, aiosqlite gallery index; HTTP/3 rejected
- [Thumbnails: drop long-lived HTTP caching instead of URL-versioning it; add an on-disk format-version marker](../notes/thumbnails-no-long-lived-http-cache.md) 2026-09-28: user chose dropping long-lived thumbnail HTTP caching over URL versioning; on-disk format marker
- [Thumbnail generation: fit-within instead of crop-fill, so the cached JPEG preserves source aspect ratio](../notes/thumbnails-fit-within.md) 2026-09-28: user required thumbnails to keep the source aspect ratio; square crop is display-only
- [Gallery item: fade-over-thumb + side nav + Loading chip](../notes/gallery-item-fade-over-thumb.md) 2026-09-28: full preview fades in over the thumb; Loading chip; side nav arrows
- [Gallery progressive preview: aspect-fit, no CSS blur, smooth scale](../notes/gallery-preview-aspect-fit.md) 2026-09-28: placeholder and full preview both aspect-fit; no CSS blur
- [Reset gallery closes SQLite before deleting index](../notes/reset-gallery-closes-sqlite.md) 2026-09-28: Reset closes the SQLite connection before deleting the index and its WAL/SHM files
- [Gallery derived caches: injective path-mirrored thumbs/exports; no cache paths in SQLite](../notes/gallery-cache-path-mirrored.md) 2026-09-26: thumb/export caches use injective path-mirrored names; no cache paths in SQLite
- [Gallery item detail: real-thumbnail-first progressive loading, photo-app open animation, slide transitions on prev/next; fixed a `.gallery-item-stage` centering regression](../notes/gallery-item-progressive-loading.md) 2026-09-25: real thumbnail first, photo-app open animation, slide transitions on prev/next
- [Gallery at 50k+ items: derived SQLite index (amends "no database"), cursor pagination, frontend DOM windowing; per-connection query lock added after finding a real concurrency bug](../notes/gallery-sqlite-index-50k.md) 2026-09-25: derived, rebuildable SQLite index (amends 'no database'), cursor paging, DOM windowing
- [Gallery item delete and Web Share export](../notes/gallery-item-delete-web-share.md) 2026-09-22: gallery item delete; desktop opens files with the OS instead of raw Download/Share
- [Gallery export separate from library convert](../notes/gallery-export-separate.md) 2026-09-22: on-demand friendly export (JPEG q95, H.264 CRF 18) cached in .exports/, separate from library convert
- [Gallery QR via segno (adapter-only)](../notes/gallery-qr-segno.md) 2026-09-22: QR codes via segno in the web adapter; lazy thumbnails under .thumbnails/

## History (superseded)
