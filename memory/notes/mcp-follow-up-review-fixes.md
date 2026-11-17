---
name: mcp-follow-up-review-fixes
description: best-effort hover enrichment, clean restart/stop, config change detected by content sha256
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

MCP follow-up review fixes.

- **Context:** Review of 072fae3 found: hover lost its text if `typeDefinition` failed; the bare-type regex matched prose and enriched every `str`; restart left in-flight requests to time out; probe cache survived a client rebuild; `touch` on a config restarted the server; stale-code check ran every call.
- **Decision:** Enrichment is best-effort (catches `LspRequestError`), rejects two-word text, skips `builtins.pyi`, lists up to 3 union members. `restart()` fails pending futures first and `stop()` awaits its reader tasks. Config changes are detected by sha256 of content. `NoticeBoard` rechecks source at most every 2 s. Line count in `InvalidPositionError` matches the check.
- **Rationale:** Optional extras must degrade, not fail; restarts should be cheap and only for real changes.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — MCP follow-up review fixes".
