_Last updated: 2026-10-06 (smart-commit-guard 0.2.0 pushed)_

## Branch

`main`. webnav starts with `npx --yes webnav-ts-mcp@^0.2.0`; codenav via `uvx` (`codenav-mcp>=0.2.0,<0.3`); jevmem pinned `>=0.3.0,<0.4`.

## Current focus

Secret gate on `smart-commit-guard` 0.2.0 (shared `pre-commit` + `commit-msg`, CI pin `>=0.2,<0.3`). Local `doctor` green.

## Just changed

- `.githooks/pre-commit` / `.githooks/commit-msg` — 0.2 shared hooks
- `.github/workflows/secret-scan.yml` — `>=0.2,<0.3`, `--messages` on PRs, `--all` on push
- `docs/agent-tooling.md`, `README.md`, memory

## Next steps

- Confirm the `secret-scan.yml` CI run on this push to `main`.
- Local Windows `task checks`: PATH-separator unit tests and `@types/node` still fail on this machine (unrelated to the gate); CI is ubuntu.
