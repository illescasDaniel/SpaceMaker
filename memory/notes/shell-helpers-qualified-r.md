---
name: shell-helpers-qualified-r
description: bare cross-module helpers qualified as R.* after the TS split
type: decision
date: 2026-09-29
status: superseded
supersedes:
superseded_by: web-ts-typing-pass-drop-r-registry
source:
---

Qualify bare cross-module shell helpers as `R.*` after the TS split.

- **Context:** Follow-up to the registry-alias fix below. User still saw gallery stuck + `ReferenceError: pushSettings is not defined`. An auditor found 22 sites where feature modules used bare identifiers (`applyState`, `pushSettings`, `loadServerInfo`) that used to be in-scope in the monolith `app.js` but are now only on the `R` registry (or defined in another module). Worst: `shell-boot.ts` chain `.then(applyState)` / `.then(loadServerInfo)` aborted desktop boot before gallery could load.
- **Decision:** Replace every bare cross-module ref with `R.<name>` in `home-bind`/`shell-boot`/`lan`/`settings`/`usb`; keep a small Python auditor heuristic for future splits; bump `UI_SHELL_VERSION`.
- **Rationale:** Same contract as the rest of the shell (`R.foo` for shared helpers). Not worth re-introducing circular ESM imports just to name-import those functions.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Qualify bare cross-module shell helpers as `R.*` after the TS split".

Superseded by [web-ts-typing-pass-drop-r-registry](web-ts-typing-pass-drop-r-registry.md).
