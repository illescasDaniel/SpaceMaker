_Last updated: 2026-10-06 (Windows unit-test PATH/.exe fixes)_

## Branch

`main`. webnav starts with `npx --yes webnav-ts-mcp@^0.2.0`; codenav via `uvx` (`codenav-mcp>=0.2.0,<0.3`); jevmem pinned `>=0.3.0,<0.4`. Secret gate on `smart-commit-guard` 0.2.0.

## Current focus

Windows pytest failures fixed (PATH `os.pathsep` + `.exe` stubs in managed/bundled tool tests). Full suite: 532 passed, 12 skipped. Commit `0dda41e` (0.2.0 gate) is still unpushed with this fix pending commit.

## Just changed

- `tests/unit/test_bundled_tools.py` — PATH tests use `os.pathsep`
- `tests/unit/test_managed_tools.py` — Windows `.exe` names + which mock accepts `ffmpeg.exe`

## Next steps

- Commit + push both commits to `main`.
- Confirm `secret-scan.yml` CI on the push.
