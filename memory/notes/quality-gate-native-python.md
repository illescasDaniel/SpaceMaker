---
name: quality-gate-native-python
description: uv run task checks runs its steps in Python, no bash needed; checks.sh kept as a mirror
type: decision
date: 2026-09-28
status: current
supersedes: quality-gate-bash-on-windows
superseded_by:
source:
---

`uv run task checks` runs natively (no bash required).

- **Context:** On Windows, `checks.py` invoked `shutil.which("bash")`, which often resolves to the WindowsApps WSL stub (`…\WindowsApps\bash.exe`). With no WSL distro installed that stub exits immediately (“no installed distributions”), so `uv run task checks` never ran the gate even when Git Bash was installed under `Program Files\Git`.
- **Decision:** Implement the quality gate steps (ruff, ty, pytest, npm check/format) directly in `scripts/quality/checks.py` via `uv`/`npm` subprocesses. Keep `checks.sh` as a bash-friendly mirror for CI/shell users; `web.sh --fix` now calls `npm run format` (there is no `fix` script).
- **Rationale:** The gate only needs Python tooling + optional Node — not a POSIX shell. Avoids PATH ordering traps between WSL stubs and Git Bash.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — `uv run task checks` runs natively (no bash required)".
