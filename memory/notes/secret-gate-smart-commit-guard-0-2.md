---
name: secret-gate-smart-commit-guard-0-2
description: smart-commit-guard 0.2: commit-msg hook too; CI scans messages on PRs and --all on push
type: decision
date: 2026-10-06
status: superseded
supersedes: secret-gate-smart-commit-guard
superseded_by: smart-commit-guard-0-3
source:
---

Secret gate upgraded to `smart-commit-guard` 0.2.0.

- **Context:** 0.2.0 adds a `commit-msg` hook, `scan --all`, `--messages` for CI, and a tighter shared-hook template; the repo still had the 0.1.0 pin and only `pre-commit`.
- **Decision:** reinstall with `smart-commit-guard install-hook --shared --force`; pin hooks and CI to `>=0.2,<0.3`; PR CI runs `--diff ... --messages`, push CI runs `--all` (replacing `--files $(git ls-files)`).
- **Rationale:** matches the upstream docs; commit messages are a real leak path; `--all` avoids argument-length limits on large trees. Local tool install is once per machine; tracked `.githooks/` still carries the gate for every clone.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-10-06 — Secret gate upgraded to `smart-commit-guard` 0.2.0".

Superseded by [smart-commit-guard-0-3](smart-commit-guard-0-3.md).
