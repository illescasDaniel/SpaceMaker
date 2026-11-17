---
name: stray-dev-server-wrong-venv
description: end-to-end check hit a dev server from another checkout's venv; verify the process path
type: incident
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

End-to-end verification caught a stray dev-server process bound to the wrong checkout's venv.

- **Context:** While end-to-end verifying the convert-media fix (below) against the user's real library, `preview_start spacemaker-server` (which runs `uv run spacemaker --server-only --port 8765` per `.claude/launch.json`) launched a process whose command line (`Get-CimInstance Win32_Process`) showed `C:\Users\kaumi\Documents\Projects\SpaceMaker\.venv\Scripts\spacemaker.exe` — the **root repo's** venv, not this worktree's own `.claude\worktrees\gallery-thumb-fix\.venv`. `spacemaker.pth` in the root venv points at the root repo's `src/`; the worktree's own venv correctly points at its own `src/`. Running Convert against that server reproduced the *original* DNG failure (moved back to `error/`), because it was silently running the unfixed code from the shared checkout — not this worktree's staging-directory/`--ignore-xmp` fix. No log file appeared either, for the same reason (that checkout's `desktop.py` may lack today's `configure_logging()` call, or simply never got the chance to run it under whatever state that process was in).
- **Decision:** For any real dev-server verification in a worktree, don't trust `preview_start`'s server to be scoped correctly — after starting it, confirm with `Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where CommandLine -like "*<port>*"` that the command line's `.venv`/`spacemaker.exe` path is under the worktree directory, not the root repo. If it isn't, stop it and start the server directly (`uv run spacemaker --server-only --port <N>` from the worktree's own cwd via the Bash tool, backgrounded) instead of relying on `preview_start`. This is what actually converted `IMG_5234.dng` and regenerated the 3 missing thumbnails correctly on the second attempt (port 8766, worktree-scoped).
- **Rationale:** Avoids a false-negative ("the fix doesn't work") or false-positive ("the fix works") verification result caused by testing against the wrong code. Not something to "fix" in the repo — it's specific to how this local machine's dev-server tooling resolves `uv run` outside the worktree's own directory context; worth remembering for future worktree-based verification in this project.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — End-to-end verification caught a stray dev-server process bound to the wrong checkout's venv".
