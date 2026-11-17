---
name: managed-tools-service-in-bootstrap
description: ManagedToolsService moved to bootstrap/services/; a clean port split would need Phase 2 approval
type: decision
date: 2026-09-29
status: current
supersedes:
superseded_by:
source:
---

Move `ManagedToolsService` from `application/` to `bootstrap/services/`.

- **Context:** `application/managed_tools.py` imported `spacemaker.bootstrap.{bundled_tools,paths,platform_setup_hints}` (layering violation surfaced by `grade_prechecks.py`). The service is inherently environment-bound (install root, `sys.platform`, bundle/dev-mode probing, on-disk setup marker), so injecting it all would have needed a new outbound port.
- **Decision:** `git mv` to `bootstrap/services/managed_tools.py` (composition-root layer, may import bootstrap); updated imports in `bootstrap/services/core.py` and `tests/unit/test_managed_tools.py`. No behavior or port changes. A future clean split (port for tool-resolution/setup-marker) needs Phase 2 approval.
- **Rationale:** Smallest behavior-preserving fix that removes the forbidden imports without a new port.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-29 — Move `ManagedToolsService` from `application/` to `bootstrap/services/`".
