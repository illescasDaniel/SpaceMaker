---
name: codenav-webnav-hardening
description: UTF-16 character columns, path:line:col, LSP error text, diagnostics fallback
type: decision
date: 2026-09-27
status: current
supersedes:
superseded_by:
source:
---

Harden codenav/webnav: character columns, path:line:col, LSP errors, diag fallback.

- **Context:** Live MCP smoke tests worked, but agents missed symbols after tab-indented lines (visual column vs character offset), `definition`/`references` headers omitted columns so follow-up calls were awkward, JSON-RPC errors looked like empty “not found”, and HTML/CSS pull diagnostics often returned empty despite push cache. Format helpers were duplicated in both servers with no unit tests.
- **Decision:** (1) Document `column` as UTF-16 character offset (tab = 1) in tool docs + `docs/agent-tooling.md`. (2) Shared `_shared/format.py`; location headers `path:line:col`; prefer LocationLink `targetSelectionRange`. (3) `LspRequestError` on JSON-RPC `error`; MCP tools return `LSP error on …`. (4) `diagnostics` falls back to `publishDiagnostics` cache when pull fails or returns empty. (5) Fast unit tests in `tests/unit/test_mcp_nav_format.py` (no live language servers).
- **Rationale:** Fixes the actual agent failure modes without inventing CSS `var(--x)` resolution or new MCP tools; shared formatters keep codenav/webnav in sync.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-27 — Harden codenav/webnav: character columns, path:line:col, LSP errors, diag fallback".
