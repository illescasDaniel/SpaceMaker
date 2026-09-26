# Progress

Open items only. Finished work: `memory/archive.md`.

## SpaceMaker app

- [x] **Gallery orphan cache cleanup** — injective path-mirrored thumbs/exports;
  in-app delete + sync GC for index/thumbs/exports; SPEC + arch approved;
  implemented on `cursor/gallery-orphan-cache-cleanup-2e72` (PR #4)
- [ ] **Easy mode import issues — where to review** — wireframe approved 2026-09-23; spec draft (open-folder API partially via `/api/library/open-folder`)
- [ ] Confirm on real Windows/macOS hardware that the native pywebview backends (`edgechromium`/`cocoa`, see `decisions.md` 2026-09-24) actually open a working window — only smoke-tested via `--server-only` in this sandbox (no GUI available here)
- [x] Gallery item detail: photo-app-style open animation (zoom+fade), slide transition on prev/next, and real-thumbnail-first progressive loading while the full image/video loads — full SDD cycle (wireframe → spec → architecture → tests → impl), all gates approved in chat. See `decisions.md` 2026-09-25.
- [x] Fix `test_given_dng_when_magick_cannot_read_then_converts_embedded_preview` — POSIX-safe magick stub (dash `${@: -1}` bashism) + fail encode on `*.dng` so embedded-preview path is exercised (test-only; production ConvertMedia/SubprocessMediaConverter OK).
