_Last updated: 2026-10-02 (grader round 1 fixed, gate green: 464 tests)_

## Branch

`claude/pre-release-code-review-024950` (worktree). Base: `main`.

## Current focus

Pre-1.0 code review fixes are done (list in `progress.md`). Next TODO: optional LAN access key/token (not started).

## Just changed

- Fixed all review + Cursor findings: settings deadlock, verified Move, same-stem collision naming + byte-identical duplicate collapse, non-overwriting moves, LAN export HTTP poll, gallery request guards, shlex-quoted ADB/AFC paths, `rmdir`-only mount cleanup, zip-slip guard, atomic export cache, ffmpeg stderr drain and µs progress fix.
- `specs/convert-media/SPEC.md`: retroactive Design decisions section, Duplicate collapse and non-overwriting move rules (amendments awaiting user review).
- New tests for all of the above (H.264 pipes, mount dirs, export poll, video collisions, content compare).

## Next steps

1. User reviews spec amendments; optionally re-run `code-grader`.
2. NEXT TODO: optional LAN access key/token (see `progress.md`).
3. Still open (deliberately skipped): tool catalog sha256 pinning, ADB list-all-roots speed-up, LAN delete/export auth (belongs to token work).
