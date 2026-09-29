_Last updated: 2026-09-29_

## Branch

`claude/web-scroll-behavior-1fc52d` (merged latest `main` quality-gate fixes; all checks green)

## Current focus

Smooth wheel scrolling feature complete. Merged main's quality-gate fixes (ruff format, MCP test names, PATH isolation). All 483 pytest tests pass.

## Next steps

Ready for PR to main. User-verified smooth scrolling on Linux (feels like Brave). Quality checks pass.

## Just changed

- Renamed `qt_webengine_gpu_flags.py` → `qt_webengine_chromium_flags.py`
- Expanded to merge `--enable-smooth-scrolling` flag (all platforms where Qt WebEngine is used)
- Updated `desktop.py` to call `install_qt_webengine_chromium_flags()`
- Updated tests (5 tests, all pass)
- Merged `main`: ruff format in `ui_shell.py`, unique MCP test names, PATH-isolated convert tests
- Updated `memory/decisions.md` and `memory/progress.md`

## Open items

None at this time. Branch ready to apply and PR.
