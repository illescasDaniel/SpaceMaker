---
name: dependency-audit-and-dependabot
description: pip-audit on the exported lock + npm audit (high) end the quality gate; weekly grouped Dependabot
type: decision
date: 2026-10-05
status: current
supersedes:
superseded_by:
source:
---

Dependency audit in the quality gate, plus Dependabot.

- **Context:** SpaceMaker had no vulnerability audit and no automated dependency updates; srxy already had `pip-audit` in its gate and a Dependabot config.
- **Decision:** `scripts/quality/checks.py` (and the `checks.sh` mirror via `audit.sh`) end with `uvx pip-audit` on `uv export --frozen --no-emit-project --all-groups --no-hashes` plus `npm audit --audit-level=high`; `--skip-audit` for offline runs. `.github/dependabot.yml` covers `uv`, `npm` and `github-actions` with weekly grouped PRs.
- **Rationale:** exporting the lock and auditing the file needs no extra dev dependency and no lockfile churn, and does not depend on what is installed locally. The first run found 0 vulnerabilities. Rejected for now: a cached audit result like srxy's (a 7-day `.gate-cache`), to keep the first version simple.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-05 — Dependency audit in the quality gate, plus Dependabot".
