_Last updated: 2026-09-29_

## Branch

`main` (then switching to `cursor/cleaner-code-with-main-2bd1`)

## Current focus

Saving the codenav/webnav external-project dogfooding fix commit to `main`, then checking out `cursor/cleaner-code-with-main-2bd1` and merging latest `main` into it.

## Next steps

- After push: checkout `cursor/cleaner-code-with-main-2bd1`, merge latest `main`, push the feature branch.
- Consider re-running `webnav_calls.json`/`codenav_calls.json` against another external project besides `srxy` before calling these MCPs release-ready for arbitrary third parties.
- Open app items remain: ADB browse slowness; Easy mode import issues; native pywebview on Win/macOS.

## Just changed

- Rebased dogfooding fixes onto `origin/main` (kept Windows `.cmd` shim resolution + typescript@5 npx pin).
- Committing: workspace-root cwd fallback, `implementations` type-verify + exclude skip, webnav JS fallback, shared `exclude.py`, outline spans, workspace-relative web index paths.
