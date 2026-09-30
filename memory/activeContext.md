_Last updated: 2026-09-30 (saved Components work)_

## Branch

`main` (primary checkout) — Components setup work committed.

## Current focus

None in-flight. Components UX polish + AFC omit + layout/PATH/hints landed.

## Just changed (this commit)

Components screen: OK chip when all tools resolve (managed or PATH); short lead; Details collapsed when OK; `setup_pending` still requires Continue for PATH-only. Also includes stepped layout, live PATH, Homebrew PATH prepend, per-tool install hints, and Linux-only AFC on Components.

## Next steps

1. Smoke: restart app → Components — OK (not WARNING) when all green/system, Details collapsed, shorter lead; no ifuse/idevice on macOS.
2. Optional: open a PR if this should leave `main` via review first (already on `main` locally).
