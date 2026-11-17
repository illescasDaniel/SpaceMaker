---
name: readme-screenshot-offscreen
description: README Home screenshot rendered offscreen with Qt WebEngine; not in CI
type: decision
date: 2026-09-23
status: current
supersedes:
superseded_by:
source:
---

README Home screenshot via offscreen WebEngine.

- **Context:** Public GitHub release needs a committed Home hub hero image that stays in sync with production UI without manual window grabs or CI WebEngine deps.
- **Decision:** `scripts/packaging/capture_readme_home_screenshot.py` starts `--server-only` in an isolated `HOME`, `POST /api/tools/components-continue`, renders at 980×920 with PyQt6 `QWebEngineView` (`QT_QPA_PLATFORM=offscreen` default); output `docs/assets/readme-home.png`; task `uv run task readme-screenshot`. Not run in AppImage CI.
- **Rationale:** Same HTML as desktop; repeatable for contributors; avoids OS window-manager automation.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-23 — README Home screenshot via offscreen WebEngine".
