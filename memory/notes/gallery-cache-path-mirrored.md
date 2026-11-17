---
name: gallery-cache-path-mirrored
description: thumb/export caches use injective path-mirrored names; no cache paths in SQLite
type: decision
date: 2026-09-26
status: current
supersedes:
superseded_by:
source:
---

Gallery derived caches: injective path-mirrored thumbs/exports; no cache paths in SQLite.

- **Context:** In-app delete already cleared `converted/` + `.thumbnails/` + the index row, but not `.exports/`. External deletes dropped index rows on sync but left both `.thumbnails/` and `.exports/` orphans. Friendly exports used opaque `sha256(path+mtime_ns+size+format)` names, which cannot be reconstructed after an external delete because the index only stores float `mtime` + size. User also asked whether thumb/export paths should be stored in `.index.sqlite` for conflict resolution.
- **Decision:** (1) Do **not** store thumbnail or export paths in the gallery index — it remains derived metadata only; filesystem is source of truth. (2) Switch both caches to **injective path-mirrored** names by appending the cache extension to the full relative path (keep original suffix): e.g. `2025/vacation.avif` → `.thumbnails/2025/vacation.avif.jpg` and `.exports/2025/vacation.avif.jpg`. (3) Reuse caches when `cache.mtime >= source.mtime`. (4) GC on in-app delete and on sync for `removed` (thumb + exports) and `changed` (exports); sweep legacy hash-named `.exports/` files on sync.
- **Rationale:** Hash names blocked reliable GC after external delete. Stem-replaced thumbs (`with_suffix(".jpg")`) already collide for `vacation.avif` vs `vacation.mp4`. Storing paths in SQLite would duplicate a pure function, go stale on naming changes, vanish on index rebuild, and not prevent on-disk collisions. Appended-suffix mirroring makes `relative_path` → cache path injective and deletable without DB state. SPEC updated first (`specs/gallery/SPEC.md`); implementation gated on explicit spec approval.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-26 — Gallery derived caches: injective path-mirrored thumbs/exports; no cache paths in SQLite".
