---
name: desktop-window-4-3-geometry
description: window geometry in one module, 4:3 default and 800x600 minimum
type: decision
date: 2026-09-23
status: current
supersedes:
superseded_by:
source:
---

Desktop window 4:3 geometry in one module.

- **Context:** Default pywebview size (980×920) felt narrow; README screenshot script duplicated width/height literals.
- **Decision:** `bootstrap/window_geometry.py` defines **1200×900** default and **800×600** minimum (both 4:3); `desktop.py` and `capture_readme_home_screenshot.py` import from there.
- **Rationale:** More horizontal room for hub/wizard layout; single source of truth for viewport parity between app and docs capture.

HEAD check 2026-11-17: `src/spacemaker/bootstrap/window_geometry.py` now sets 1152x864 (still 4:3) with an 800x600 minimum; the code wins over the sizes above.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — Desktop window 4:3 geometry in one module".
