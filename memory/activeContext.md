_Last updated: 2026-09-24_

## Branch

`main`

## Current focus

Saved a large batch of previously-uncommitted local work via `/save-changes`. Verified all tests pass on Windows (164 pass, 5 skipped as POSIX-only) and the full quality gate (`uv run task checks`) runs natively on Windows and is green (ruff, ty, pytest). Committed in logical groups: Windows dev/test compatibility, QR dark-theme/flash fix + Windows component setup (exiftool download, ImageMagick PATH fallback, winget hints) + Easy-mode Wi‑Fi session fix, Qt WebEngine shutdown hardening, and the `.claude/skills` symlink. See `decisions.md` (2026-09-24 entries) for what each group covers and why.

## Just changed (now committed, see decisions.md)

- Windows compat: `bootstrap/paths.py` `display_user_path` normalises separators to `/`; `scripts/quality/checks.py` dispatches through `bash` on `win32`; platform-appropriate stub filenames / `@_skip_on_windows` markers across several unit tests.
- QR codes: `adapters/inbound/web/qr_svg.py` (opaque black/white SVG, replacing theme-matched colors) + `app.js` `setQrImageSrc()` dedup so `<img src>` isn't reassigned every poll; `index.html` `aspect-ratio: 1` + `background: #fff` around QR images.
- Windows component setup: `packaging/tool-catalog.json` exiftool entry + fixed ffmpeg URL; `catalog_installer.py` `zip_flatten` strategy + clearer 404 errors; `bundled_tools.py` ImageMagick Program-Files fallback; new `bootstrap/platform_setup_hints.py` (winget command surfaced in Components UI via `managed_tools.py` `setup_hint` + `app.js` `renderComponentsSetupHint`).
- `bootstrap/services.py` — `start_convert` only stops an active extract job under `STOP_EXTRACT_FIRST`, fixing Easy-mode dropping the Wi‑Fi upload session on the first convert-as-received trigger.
- `adapters/inbound/qt_webengine_shutdown.py` + `desktop.py` — much more thorough WebEngine/Qt teardown (idempotent, disconnects webchannel/nav-handler/interceptor, deletes top-level widgets) plus a `finalize_qt_after_webview()` pass after pywebview's loop exits; Windows gets longer drain rounds and real sleeps for `QDxgiVSyncService`.
- `.claude/skills` — real Windows symlink → `.cursor/skills` so Claude Code's project-skill discovery sees this repo's Cursor-authored skills.

## Next steps

1. **Easy mode import issues — where to review** — spec draft pending (open-folder API partially via `/api/library/open-folder`); wireframe already approved 2026-09-23.
2. No other known blockers from this session; tree should be clean after this save.

## Run

```bash
uv run task spacemaker
uv run pytest        # 164 passed, 5 skipped (Windows)
uv run task checks   # ruff + ty + pytest, works natively on Windows
```

## Notes for Claude Code specifically (this machine)

- Project skills live at `.cursor/skills/` (Cursor's convention); Claude Code only auto-discovers `.claude/skills/`. Fixed via a real OS symlink `.claude/skills -> .cursor/skills` (needs an elevated shell to (re)create on a fresh clone — `New-Item -ItemType SymbolicLink -Path ".claude\skills" -Target ".cursor\skills"` after `mkdir .claude`).
- No `.claude/skills` fallback exists for instructions files: Claude Code already reads `AGENTS.md` directly when there's no `CLAUDE.md`, confirmed by this session loading `AGENTS.md` with no `CLAUDE.md` present — a `CLAUDE.md -> AGENTS.md` symlink is unnecessary and was intentionally skipped.
