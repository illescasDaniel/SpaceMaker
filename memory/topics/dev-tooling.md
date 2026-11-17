# Dev tooling and quality gate
Updated: 2026-11-17. Quality gate, secret scanning, dependency audit, worktrees and docs build.

## Now
`uv run task checks` runs natively in Python ([quality-gate-native-python](../notes/quality-gate-native-python.md)) and ends with a dependency audit ([dependency-audit-and-dependabot](../notes/dependency-audit-and-dependabot.md)); secrets are gated by smart-commit-guard 0.3 ([smart-commit-guard-0-3](../notes/smart-commit-guard-0-3.md)); linked worktrees sync deps by lockfile stamp ([worktree-deps-lock-stamped](../notes/worktree-deps-lock-stamped.md)).

## How it got here
- 2026-09-24 Windows gate ran through bash, replaced on 2026-09-28 by native Python steps ([note](../notes/quality-gate-native-python.md)).
- 2026-10-05 secret gate 0.1 → 0.2 (2026-10-06) → 0.3 (2026-10-08) ([note](../notes/smart-commit-guard-0-3.md)).

## Notes
- [Secret gate on smart-commit-guard 0.3](../notes/smart-commit-guard-0-3.md) 2026-10-08: secret gate on smart-commit-guard >=0.3,<0.4 (autostarts the local model); commit-msg hook must be 755
- [Dependency audit in the quality gate, plus Dependabot](../notes/dependency-audit-and-dependabot.md) 2026-10-05: pip-audit on the exported lock + npm audit (high) end the quality gate; weekly grouped Dependabot
- [JS unit tests: vitest + jsdom, unlock assets externalized](../notes/js-tests-vitest-jsdom.md) 2026-10-02: first JS tests (vitest + jsdom) because the passcode UI is security-relevant
- [MkDocs build stays warning-free](../notes/mkdocs-build-warning-free.md) 2026-09-30: the mkdocs docs build must stay warning-free
- [Worktree deps: lock-stamped `node_modules`, always-`uv sync` `.venv`](../notes/worktree-deps-lock-stamped.md) 2026-09-29: node_modules copied only when lockfiles match (stamp), else npm ci; .venv always uv sync
- [`uv run task checks` runs natively (no bash required)](../notes/quality-gate-native-python.md) 2026-09-28: uv run task checks runs its steps in Python, no bash needed; checks.sh kept as a mirror
- [Quality gate stale-failures fix: `gallery_cache_paths` outputs are OS-native filesystem paths, not URL fragments; CRLF was a local checkout artifact, not repo content](../notes/quality-gate-stale-failures-test-bugs.md) 2026-09-28: stale gate failures were test bugs (OS-native paths) and a local CRLF checkout artifact
- [`/new-worktree` skill: create worktree+branch then copy/regenerate `.venv`+`node_modules`](../notes/new-worktree-skill.md) 2026-09-28: /new-worktree forks from the current branch, then copies or regenerates .venv and node_modules
- [End-to-end verification caught a stray dev-server process bound to the wrong checkout's venv](../notes/stray-dev-server-wrong-venv.md) 2026-09-28: end-to-end check hit a dev server from another checkout's venv; verify the process path
- [uv quality gate and Biome for web](../notes/uv-quality-gate-biome.md) 2026-09-22: uv task quality gate (ruff, ty, pytest) and Biome for web

## History (superseded)
- [Secret gate upgraded to `smart-commit-guard` 0.2.0](../notes/secret-gate-smart-commit-guard-0-2.md) 2026-10-06 → superseded by smart-commit-guard-0-3
- [Secret gate: `smart-commit-guard` via a tracked `.githooks/pre-commit` plus a CI scan](../notes/secret-gate-smart-commit-guard.md) 2026-10-05 → superseded by secret-gate-smart-commit-guard-0-2
- [`uv run task checks` dispatches via bash on native Windows](../notes/quality-gate-bash-on-windows.md) 2026-09-24 → superseded by quality-gate-native-python
