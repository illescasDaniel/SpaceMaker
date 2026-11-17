---
name: webnav-npx-pin-typescript-5
description: npx typescript-language-server fallback pinned typescript@5
type: decision
date: 2026-09-28
status: superseded
supersedes:
superseded_by: typescript-7-native-tsc-lsp
source:
---

webnav's npx `typescript-language-server` fallback must pin and bundle `typescript@5`.

- **Context:** While live-verifying the fix for webnav's `search_symbol` "No Project" bug against a real external project (`srxy`, no local `typescript` install), the `npx --yes typescript-language-server` fallback started the binary fine but then failed at LSP `initialize` with "Could not find a valid TypeScript installation" — `typescript-language-server` needs `typescript` as a peer dependency it does not bundle, and resolves it from the *workspace's* own `node_modules`, not from wherever the server binary itself came from. Bundling `-p typescript` (unpinned) alongside it in the same `npx` invocation seemed like the fix, but that resolved TypeScript 7.x — a native-compiler preview with a different package layout (no `lib/tsserverlibrary.js`) — which broke resolution the same way for a different reason.
- **Decision:** `lang_command.py`'s `resolve_ts_command` npx fallback now runs `npx --yes -p typescript@5 -p typescript-language-server typescript-language-server --stdio`, pinning the bundled TypeScript to the 5.x line.
- **Rationale:** A workspace with no local `typescript` (increasingly the norm for non-TS-project JS files, e.g. plain vanilla-JS static assets) needs the npx fallback to be fully self-sufficient rather than silently depending on an incidental global/local install. Pinning to `@5` avoids a second, subtler failure mode from an unpinned `-p typescript` resolving the incompatible 7.x preview. Verified live: `search_symbol` as the very first call against real `srxy` now succeeds end-to-end with no env vars and no pre-existing `typescript` install anywhere in the environment.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — webnav's npx `typescript-language-server` fallback must pin and bundle `typescript@5`".

Superseded by [typescript-7-native-tsc-lsp](typescript-7-native-tsc-lsp.md).
