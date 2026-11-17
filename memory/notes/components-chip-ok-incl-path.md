---
name: components-chip-ok-incl-path
description: Components chip is OK when every tool resolves, PATH included; WARNING kept in the enum but not emitted
type: decision
date: 2026-09-30
status: current
supersedes:
superseded_by:
source:
---

Components chip OK when all tools resolve (incl. PATH).

- **Context:** Aggregate chip showed WARNING whenever any tool was system PATH-only, even with 0 missing and all-green rows; Details stayed expanded. Users read that as an error.
- **Decision:** `summarize_tool_resolutions` returns OK when every resolution is managed or PATH; MISSING only when any is unresolved. Keep `ToolsSummaryStatus.WARNING` in the enum for legacy clients but do not emit it. `setup_pending` no longer keys off the chip — it stays true until Continue when any tool is PATH (or missing / downloads pending), so convert PATH fallback remains gated. No new ports. Lead copy + Details default follow chip OK (UI Phase 4).
- **Rationale:** Matches approved wireframe/spec; managed vs system stays visible in the summary counts line without a scary chip; Continue trust gate must not depend on WARNING.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-30 — Components chip OK when all tools resolve (incl. PATH)".
