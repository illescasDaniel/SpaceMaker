---
name: search-symbol-decorator-lines
description: search_symbol walks past decorator lines to the name column
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

search_symbol: walk past decorator lines for name column.

- **Context:** Live `search_symbol("LspClient")` returned `lsp_client.py:45:1` (`@dataclass`); hover/definition/references at that column were empty. Name-column logic only searched the LSP range-start line.
- **Decision:** Shared `_name_position` searches within `location.range` then up to 8 lines past start for the identifier; unit tests for decorator + stacked decorators; ty integration smoke for `@dataclass class SmokeDecorated`.
- **Rationale:** ty SymbolInformation often starts on decorators; agents chain search → hover and need the real name column without reimplementing LSP.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — search_symbol: walk past decorator lines for name column".
