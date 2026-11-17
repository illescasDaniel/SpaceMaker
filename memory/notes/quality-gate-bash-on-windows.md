---
name: quality-gate-bash-on-windows
description: task checks dispatched through bash on native Windows
type: decision
date: 2026-09-24
status: superseded
supersedes:
superseded_by: quality-gate-native-python
source:
---

`uv run task checks` dispatches via bash on native Windows.

- **Context:** `scripts/quality/checks.py` ran `checks.sh` directly as `subprocess.call([str(script)], ...)`, which relies on the POSIX shebang; on native Windows Python (not inside Git Bash) this fails with `OSError: [WinError 193] %1 is not a valid Win32 application`, silently blocking the whole quality gate (ruff/ty/pytest/web) for anyone running `uv run task checks` from PowerShell/cmd.
- **Decision:** When `sys.platform == "win32"`, prepend `shutil.which("bash")` to the command (erroring clearly if bash isn't on `PATH`); Unix keeps calling `checks.sh` directly.
- **Rationale:** `checks.sh` itself is fine under bash (verified — ruff/ty/pytest/web all pass on Windows via Git Bash); the dispatcher just needed to route through an interpreter that understands the shebang. Git Bash is already assumed elsewhere in this repo's Windows workflow.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-24 — `uv run task checks` dispatches via bash on native Windows".

Superseded by [quality-gate-native-python](quality-gate-native-python.md).
