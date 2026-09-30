---
date: 2026-09-30
area: codenav
severity: blocked
status: fixed (branch claude/mcp-tools-pypi-review-727d33)
---

**Call:** any codenav tool, server installed from the built wheel into a clean venv and started in a project without its own `.venv/bin/ty` (the `uvx codenav-mcp` case)
**Expected:** ty (a declared dependency) is used
**Got:** `language server exited: uv run ty server` on every tool. `resolve_ty_command` only checked the workspace `.venv` and `PATH`, and the tool env isn't on PATH; its `uv run ty server` fallback fails outside a uv project that declares ty (`Failed to spawn: ty`), while its log claimed it "installs it on first use". In-repo runs never showed this because SpaceMaker's own `.venv/bin/ty` is found first.
**Workaround:** none for end users
**Idea:** done: resolve the bundled ty via `ty.find_ty_bin()`, fall back to `uvx ty server`, and quote the language server's last stderr lines in the exit error. Test publishable packages from wheels outside the repo.
