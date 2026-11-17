---
name: typescript-7-native-tsc-lsp
description: web tooling on TypeScript 7; webnav launches tsc --lsp --stdio instead of typescript-language-server
type: decision
date: 2026-09-30
status: current
supersedes: webnav-npx-pin-typescript-5
superseded_by:
source:
---

TypeScript 7 CLI + webnav native `tsc` LSP.

- **Context:** SpaceMaker was on TypeScript 5.9 with webnav launching `typescript-language-server` (classic `tsserver.js`). TypeScript 7.0.2 is stable on npm (`tsc` is a Go native binary; no `tsserver.js`). Native LSP is `tsc --lsp --stdio`. webnav must launch independently of SpaceMaker's root `node_modules`.
- **Decision:** (1) Root `package.json`: `typescript@^7.0.2`, drop `typescript-language-server`, `engines.node >= 18`. (2) webnav owns `mcp-servers/webnav_mcp/package.json` with `typescript@^7` + `vscode-langservers-extracted`. (3) `resolve_ts_command` resolution: workspace TS7 `tsc` → webnav package `tsc` → PATH TS7 → `npx -p typescript@7 tsc --lsp --stdio`. (4) Keep eager-open of jsconfig includes; native LSP also supports pull diagnostics (LspClient already prefers pull).
- **Rationale:** Single modern compiler for check/emit; webnav does not depend on a dead classic TLS peer; standalone launch keeps working via package-local install or npx.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — TypeScript 7 CLI + webnav native `tsc` LSP".
