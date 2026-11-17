---
name: mcp-refresh-skips-nested-checkouts
description: refresh walk prunes nested .git dirs; probe document at the workspace root
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

MCP refresh walk skips nested checkouts; probe document at the workspace root.

- **Context:** The per-call `LspClient.refresh()` walk measured ~20 ms on the user's machine vs ~7 ms on a clean clone. Cause: linked worktrees live inside the primary (`.claude/worktrees/<slug>`), so the primary's walk stat'ed every worktree's files (one worktree: 7 → 17 ms) and reported their edits to ty as if they were this workspace's; a `resolve()` per file was another ~⅔ of the remaining cost. Separately, the `implementations` probe document sat at `mcp-servers/.codenav_probe.py` (SpaceMaker-specific; git history gives no reason) while the docs said `<root>/.codenav_probe.py`.
- **Decision:** `_scan_watched` is a `scandir` walk that resolves the root once (only symlinked files get their own `resolve()`) and prunes any directory below the root that holds a `.git` entry. The probe moves to `<root>/.codenav_probe.py`. Rejected: scoping the walk to source/test roots (would miss edits elsewhere ty still indexes, e.g. `scripts/`), and debouncing (a quick edit between two calls could be missed).
- **Rationale:** A nested `.git` marks another repository/checkout, never this workspace's source, so pruning is correct as well as cheaper (~2.3 ms regardless of worktrees). The probe's imports are absolute, so its directory never affected resolution; the root is also clear of path-scoped ty overrides (`tests/**`). Verified: live-ty tests and real-repo `implementations` output unchanged.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — MCP refresh walk skips nested checkouts; probe document at the workspace root".
