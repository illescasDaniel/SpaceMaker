---
name: search-symbol-name-columns
description: search_symbol name columns, kind labels, 50-result cap, live ty smoke
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

search_symbol: name columns, kind labels, result cap, live ty smoke.

- **Context:** Live MCP smoke showed `codenav` `search_symbol` returning ty's SymbolInformation range start (`class` at column 1). Chaining that column into hover/definition/references returned empty; the identifier column worked. Search also omitted kind and could dump unbounded lists. HTML/CSS still lack useful `workspace/symbol`.
- **Decision:** (1) Shared `format_workspace_symbol(s)`: prefer `selectionRange`, else find `name` on the range line, else `range.start`; include LSP SymbolKind label; cap at 50 with “and N more”. (2) Both MCP servers use the helper. (3) Fast unit tests + skippable integration smoke starting `ty` on a tiny temp workspace. (4) Document that webnav does not reimplement HTML/CSS symbol search. (5) `LspClient.stop` waits for process exit.
- **Rationale:** Agents' typical flow is search → hover/refs; keyword columns break that for ty. Kind/cap improve scanability without new tools. Live smoke stays opt-in via integration mark; no HTML/CSS indexer invented.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — search_symbol: name columns, kind labels, result cap, live ty smoke".
