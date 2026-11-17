---
name: smart-commit-guard-0-3
description: secret gate on smart-commit-guard >=0.3,<0.4 (autostarts the local model); commit-msg hook must be 755
type: decision
date: 2026-10-08
status: current
supersedes: secret-gate-smart-commit-guard-0-2
superseded_by:
source:
---

On 2026-10-08 smart-commit-guard 0.3.0 was adopted: pins bumped to `>=0.3,<0.4` in the hooks, `.github/workflows/secret-scan.yml` and the docs; the `commit-msg` hook mode was fixed to 755; the public build was verified to start the local model on demand. Confirmed at HEAD on 2026-11-17: `secret-scan.yml` pins `>=0.3,<0.4`.

Source: `memory/progress.md` (2026-10-08 item); no `decisions.md` entry existed.
