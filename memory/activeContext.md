_Last updated: 2026-10-05 (README smart-commit-guard link)_

## Branch

`main`. webnav starts with `npx --yes webnav-ts-mcp@^0.2.0`; codenav via `uvx` (`codenav-mcp>=0.2.0,<0.3`); jevmem pinned `>=0.3.0,<0.4`.

## Current focus

Secret gate is on `main` (commit `a51af8e`): tracked `.githooks/pre-commit`, CI workflow, docs. README now links [`smart-commit-guard`](https://github.com/illescasDaniel/smart-commit-guard) under Development tooling.

## Just changed

- `README.md` — short reference + repo link for the pre-commit/CI secret scan.

## Next steps

- Confirm the first real `secret-scan.yml` CI run on a PR/push.
- Optional (upstream): add the `uvx` install + CI example to the smart-commit-guard README.
- Ideas still open: codenav skipping gitignored paths (e.g. `site/`) in the rename mention scan; jevmem README known limitations.
