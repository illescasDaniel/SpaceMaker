---
name: uv-quality-gate-biome
description: uv task quality gate (ruff, ty, pytest) and Biome for web
type: decision
date: 2026-09-22
status: current
supersedes:
superseded_by:
source:
---

uv quality gate and Biome for web.

- **Context:** User requested srxy-style uv/ruff/ty checks plus JS lint for web UI.
- **Decision:** `pyproject.toml` + `uv run task checks` (`scripts/quality/checks.sh`: ruff, ty, pytest). Web: `package.json` + Biome 2.x on wireframes and future `static/` JS.
- **Rationale:** Matches Astral toolchain on Python; single fast linter/formatter for vanilla JS without separate ESLint+Prettier until needs grow.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-22 — uv quality gate and Biome for web".
