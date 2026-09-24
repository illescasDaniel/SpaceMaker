_Last updated: 2026-09-24_

## Branch

`main`

## Current focus

Suppressed the two known-benign `QDxgiVSyncService`/`QThreadStorage` Qt shutdown
warnings on Windows (previously investigated and left as-is, see `decisions.md`).
User re-reported them, confirmed on questioning they're still just console noise
(no hang/crash/bad exit), so the fix is a targeted log filter, not a re-opening of
the async-DXGI-teardown-race investigation:

- `qt_webengine_shutdown.py`: new `_is_benign_shutdown_warning()` (pure predicate)
  and `install_benign_shutdown_warning_filter()` (`QtCore.qInstallMessageHandler`
  wrapper that drops only the two known message prefixes, forwards everything else
  to the previously-installed handler). Wired in from
  `install_qt_webengine_shutdown_fix()`. No change to `finalize_qt_after_webview()`,
  `finish_quit()`, or any drain/sleep timing.
- Tests added to `tests/unit/test_qt_webengine_shutdown.py` (4 new cases: predicate
  matching + handler forwarding via a monkeypatched `qInstallMessageHandler`).
- Verified: `uv run task checks` green (ruff, ty, 182 tests incl. the 4 new ones);
  user ran the real desktop app, closed the window, confirmed the two lines are
  gone and the window still closes promptly.
- `memory/decisions.md` updated (new entry, narrows the earlier "not pursuing
  further" decision).

No domain/port/architecture change — stayed entirely inside the existing inbound
desktop adapter, so no new Phase Gate was needed (same precedent as the prior
shutdown-hardening commits).

## Next steps (this thread)

None — this thread is complete, being committed now via `/save-changes`.

## Run

```bash
uv run task spacemaker
uv run task docs-serve              # docs site at http://127.0.0.1:8000/ (humans; agents read docs/*.md directly)
uv run task graph-explain "<symbol>" # or: graph-path "<a>" "<b>", graph-query "<question>"
uv run task checks                  # ruff + ty + pytest, works natively on Windows
uv run task smoke                   # real-process server smoke test (subset of checks)
```

## Notes for Claude Code specifically (this machine)

- Project skills live at `.cursor/skills/` (Cursor's convention); Claude Code only auto-discovers `.claude/skills/`. Fixed via a real OS symlink `.claude/skills -> ../.cursor/skills` (relative target, portable across machines/OS). `git checkout` recreates it correctly on any clone.
- Older finished threads (Graphify/MkDocs adoption, the `.claude/skills` symlink fix, Windows desktop-bug dogfooding, gotchas): `memory/archive.md` and `docs/agent-tooling.md`.
