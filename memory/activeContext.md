_Last updated: 2026-10-02 (network passcode committed, grader PASS, gate green)_

## Branch

`main`. Pushed at end of this session.

## Current focus

Network passcode feature is complete and committed (`1e7132e`, `0bc8298`); awaiting user review. Phase 5 grader PASS on the final state.

## Just changed

- Unlock page CSS/JS externalized (`static/unlock.css`, `web/src/unlock.ts`); exempt paths are exactly `/api/unlock`, `/favicon.ico`, `/static/unlock.css`, `/static/js/unlock.js` (spec line updated, approved).
- First JS tests: vitest + jsdom in `web/tests/` (`npm run test:web`, part of `npm run check`). Info button fixed (`.info-panel.visible`), dock Active copy is now "Active".
- Earlier: pre-1.0 review fixes and `convert-media` spec amendments (see `progress.md`).

## Next steps

1. User reviews the passcode feature (click the dock info button in the real app).
2. Add JS tests for other `web/src` modules (start with `dom.ts`).
3. Still open (deliberately skipped): tool catalog sha256 pinning, ADB list-all-roots speed-up, LAN delete/export auth beyond the passcode.
