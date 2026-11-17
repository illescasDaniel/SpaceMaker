---
name: webnav-windows-cmd-shims
description: webnav prefers npm .cmd shims on Windows
type: decision
date: 2026-09-28
status: current
supersedes:
superseded_by:
source:
---

webnav: prefer npm `.cmd` shims on Windows.

- **Context:** Live smoke on Windows found webnav's JS/HTML/CSS language servers failing with `File not found: None` / WinError 193. Two stacked causes: (1) incomplete `node_modules` (only Biome present — language-server packages never installed), so resolution fell through to bare `npx`; (2) even after `npm ci`, `_resolve_bin` preferred the extensionless POSIX shim under `node_modules/.bin/`, which `CreateProcess` cannot run (WinError 193 "%1 is not a valid Win32 application"). `format_tool_error` also rendered spawn failures without a filename as the misleading `Cannot read None: …`.
- **Decision:** Prefer `{bin}.cmd` before the extensionless shim when `sys.platform == "win32"`; resolve `npx` via `shutil.which` in the fallback; improve spawn-error text when `exc.filename` is None. Documented in `docs/agent-tooling.md`. Unit tests in `webnav_mcp/tests/test_lang_command.py`.
- **Rationale:** Matches how Windows npm actually lays out `.bin/` and how CreateProcess works; keeps the POSIX path unchanged. Incomplete installs remain a local hygiene issue (`npm ci`), not something the resolver can invent binaries for.

Migrated 2026-11-17 from `memory/decisions.md`, entry "2026-09-28 — webnav: prefer npm `.cmd` shims on Windows".
