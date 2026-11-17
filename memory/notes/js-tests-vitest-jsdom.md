---
name: js-tests-vitest-jsdom
description: first JS tests (vitest + jsdom) because the passcode UI is security-relevant
type: decision
date: 2026-10-02
status: current
supersedes:
superseded_by:
source:
---

JS unit tests: vitest + jsdom, unlock assets externalized.

- **Context:** the repo had zero JS tests; the passcode dock/unlock/auth-guard logic is security-relevant UI.
- **Decision:** `web/tests/*.test.ts` run by vitest (jsdom) via `npm run test:web`, part of `npm run check` and the quality gate. Unlock page CSS/JS and the auth guard are real files (`static/unlock.css`, `web/src/unlock.ts`, `web/src/auth-guard.ts`); the passcode middleware exempts exactly `/api/unlock`, `/favicon.ico`, `/static/unlock.css`, `/static/js/unlock.js`.
- **Rationale:** matches the approved spec's exempt list, keeps everything in conventional folders, and makes the logic testable by injecting `fetch`/`location`.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-02 — JS unit tests: vitest + jsdom, unlock assets externalized".
