_Last updated: 2026-09-30 (MCP packages verified pre-publish; pushing `main`)_

## Branch

`main` (primary checkout). Contains the Components UX work (`2d519d6`) and the merged MCP PyPI readiness pass.

## Current focus

Publish the MCP packages. Pre-publish verification is done: 3 wheels rebuilt (LICENSE, `py.typed`, console scripts, pins OK); clean py3.11 venv with minimal PATH: `codenav-mcp` finds its bundled `ty`; shared 159 / codenav 46 / webnav 116 unit tests and `task checks` green; live webnav `references`/`definition` on HTML `id=` and codenav error paths OK.

## Next steps

1. Publish (needs your PyPI token): `uv build --package mcp-nav-shared`, then `codenav-mcp`, `webnav-mcp` into a scratch `dist/`; `uv publish` the shared package first. Consider TestPyPI first. Then check `uvx codenav-mcp` / `uvx webnav-mcp` in a non-uv project.
2. Components smoke (not yet done): restart the app → Components shows OK (not WARNING) when all tools resolve/system, Details collapsed, shorter lead; no ifuse/idevice on macOS.

## Older open items

- Trial `code-grader` on the next real SDD feature.
- Exercise the `npm ci` fallback in `copy-venv.sh` next time a branch changes `package-lock.json`.
- Real-app check of the gallery delete animation on the user's library.
- Older open items in `progress.md` (ADB Browse slowness; Easy mode import; native pywebview hardware smoke).
